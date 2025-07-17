#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// Input parameters
params.references = null
params.reads = null
params.outdir = "results"
params.kmer = 31
params.plot = true

if (!params.references) {
    error "Please provide a references file with --references"
}
if (!params.reads) {
    error "Please provide a reads file or directory with --reads"
}

// Create sourmash signatures from reference FASTA files
process sketch_references {
    conda 'bioconda::sourmash conda-forge::sourmash_plugin_branchwater'

    input:
    path references

    output:
    path "refs.sig"

    script:
    """
    sourmash sketch dna \\
        --singleton \\
        -p k=${params.kmer},scaled=100,noabund \\
        -o refs.sig \\
        ${references}
    """
}

// Create sourmash signatures from read FASTQ files
process sketch_reads {
    conda 'bioconda::sourmash conda-forge::sourmash_plugin_branchwater'

    input:
    path reads

    output:
    tuple path(reads), path("reads.sig")

    script:
    """
    sourmash scripts singlesketch \\
        -p k=${params.kmer},scaled=100,noabund,dna \\
        -o reads.sig \\
        ${reads}
    """
}

// Calculate containment between reads and references
process calculate_containment {
    memory { 4.GB * task.attempt }
    maxRetries 3
    errorStrategy { task.exitStatus in 137..140 ? 'retry' : 'terminate' }

    conda 'bioconda::sourmash conda-forge::sourmash_plugin_branchwater'

    input:
    tuple path(reads), path(reads_sig, stageAs: 'reads_signature.sig')
    path refs_sig, stageAs: 'refs_signature.sig'

    output:
    tuple path(reads), path("containment.csv")

    script:
    """
    sourmash search \\
        --max-containment \\
        -t 0.0 \\
        -o containment.csv \\
        reads_signature.sig \\
        ${refs_sig}
    """
}

// Generate individual visualization for each sample
process plot {
    publishDir "${params.outdir}", mode: 'copy'

    conda 'conda-forge::pandas conda-forge::altair conda-forge::vl-convert-python'

    input:
    tuple path(reads), path(containment_csv)
    path plot_script

    output:
    path "${reads.baseName.replaceAll(/\.(fastq|fq)$/, '')}.png", optional: true
    path "${reads.baseName.replaceAll(/\.(fastq|fq)$/, '')}.csv"

    script:
    """
    python ${plot_script} ${containment_csv} \\
        --output-plot ${reads.baseName.replaceAll(/\.(fastq|fq)$/, '')}.png \\
        --output-csv ${reads.baseName.replaceAll(/\.(fastq|fq)$/, '')}.csv \\
        --title-prefix ${reads.baseName.replaceAll(/\.(fastq|fq)$/, '')} \\
        --kmer ${params.kmer} \\
        ${params.plot ? '' : '--no-plot'}
    """
}

// Generate combined visualization for all samples
process plot_combined {
    publishDir "${params.outdir}", mode: 'copy'

    conda 'conda-forge::pandas conda-forge::altair conda-forge::vl-convert-python'

    input:
    path containment_csvs
    path plot_script

    output:
    path "containment.png", optional: true
    path "containment.csv"

    script:
    """
    python ${plot_script} ${containment_csvs.join(' ')} \\
        --output-plot containment.png \\
        --output-csv containment.csv \\
        --combined \\
        --kmer ${params.kmer} \\
        ${params.plot ? '' : '--no-plot'}
    """
}

workflow {
    references_ch = Channel.fromPath(params.references, checkIfExists: true)
    plot_script_ch = Channel.fromPath("$projectDir/plot_containment.py", checkIfExists: true)

    // Handle both single files and directories of FASTQ files
    reads_path = file(params.reads)
    if (reads_path.isDirectory()) {
        reads_ch = Channel.fromPath("${params.reads}/*.{fastq,fq,fastq.gz,fq.gz}", checkIfExists: true)
    } else {
        reads_ch = Channel.fromPath(params.reads, checkIfExists: true)
    }

    // Skip sketching if input is already a signature file
    if (params.references.endsWith('.sig')) {
        refs_sig = references_ch
    } else {
        refs_sig = sketch_references(references_ch)
    }

    if (params.reads.endsWith('.sig')) {
        reads_with_sig = reads_ch.map { reads -> tuple(reads, reads) }
    } else {
        reads_with_sig = sketch_reads(reads_ch)
    }

    // Main workflow: containment calculation and visualization
    containment_with_reads = calculate_containment(reads_with_sig, refs_sig.first())
    
    if (params.plot) {
        (plot_pngs, plot_csvs) = plot(containment_with_reads, plot_script_ch.first())
        
        // Create combined plot only for directory input
        if (reads_path.isDirectory()) {
            all_csvs = plot_csvs.collect()
            plot_combined(all_csvs, plot_script_ch)
        }
    } else {
        // Just process CSV files without plotting
        (plot_pngs, plot_csvs) = plot(containment_with_reads, plot_script_ch.first())
    }
}

workflow.onComplete {
    println "🦜🦜🦜"
}