#!/usr/bin/env nextflow

nextflow.enable.dsl = 2
params.references = null
params.reads = null
params.outdir = "results"
params.kmer = 31

if (!params.references) {
    error "Please provide a references file with --references"
}
if (!params.reads) {
    error "Please provide a reads file with --reads"
}

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
    echo "Input files:"
    ls -la
    echo "Running sourmash search..."
    sourmash search \\
        --max-containment \\
        -t 0.0 \\
        -o containment.csv \\
        reads_signature.sig \\
        ${refs_sig}

    echo "Output file info:"
    ls -la containment.csv
    echo "CSV content:"
    cat containment.csv
    """
}

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
        --debug
    """
}

workflow {
    references_ch = Channel.fromPath(params.references, checkIfExists: true)
    reads_ch = Channel.fromPath(params.reads, checkIfExists: true)
    plot_script_ch = Channel.fromPath("$projectDir/plot_containment.py", checkIfExists: true)

    // Check if reads file is a signature
    if (params.references.endsWith('.sig')) {
        refs_sig = references_ch
    } else {
        // We must first sketch
        refs_sig = sketch_references(references_ch)
    }

    // Check if reads file is a signature
    if (params.reads.endsWith('.sig')) {
        reads_with_sig = reads_ch.map { reads -> tuple(reads, reads) }
    } else {
        // We must first sketch
        reads_with_sig = sketch_reads(reads_ch)
    }

    containment_with_reads = calculate_containment(reads_with_sig, refs_sig)
    plot(containment_with_reads, plot_script_ch)
}

workflow.onComplete {
    println "🦜🦜🦜"
}