#!/usr/bin/env nextflow

nextflow.enable.dsl = 2
params.references = null
params.reads = null
params.outdir = "results"

if (!params.references) {
    error "Please provide a references file with --references"
}
if (!params.reads) {
    error "Please provide a reads file with --reads"
}

process sketch_references {
    tag "sketch_refs"

    conda 'bioconda::sourmash'

    input:
    path references

    output:
    path "refs.sig"

    script:
    """
    sourmash sketch dna \\
        --singleton \\
        -p k=31,scaled=100,noabund \\
        -o refs.sig \\
        ${references}
    """
}

process sketch_reads {
    tag "sketch_reads"

    conda 'bioconda::sourmash'

    input:
    path reads

    output:
    tuple path(reads), path("reads.sig")

    script:
    """
    sourmash sketch dna \\
        -p k=31,scaled=100,noabund \\
        -o reads.sig \\
        ${reads}
    """
}

process calculate_containment {
    tag "containment"

    conda 'bioconda::sourmash'

    input:
    tuple path(reads), path(reads_sig)
    path refs_sig

    output:
    tuple path(reads), path("containment.csv")

    script:
    """
    echo "Input files:"
    ls -la
    echo "Reads signature info:"
    sourmash sig describe ${reads_sig}
    echo "References signature info:"
    sourmash sig describe ${refs_sig}

    echo "Running sourmash search..."
    sourmash search \\
        --max-containment \\
        -t 0.0 \\
        -o containment.csv \\
        ${reads_sig} \\
        ${refs_sig}

    echo "Output file info:"
    ls -la containment.csv
    echo "CSV content:"
    cat containment.csv
    """
}

process plot {
    tag "plot"
    publishDir "${params.outdir}", mode: 'copy'

    conda 'conda-forge::altair conda-forge::pandas conda-forge::vl-convert-python'

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
        --debug
    """
}

workflow {
    references_ch = Channel.fromPath(params.references, checkIfExists: true)
    reads_ch = Channel.fromPath(params.reads, checkIfExists: true)
    plot_script_ch = Channel.fromPath("$projectDir/plot_containment.py", checkIfExists: true)
    refs_sig = sketch_references(references_ch)
    reads_with_sig = sketch_reads(reads_ch)
    containment_with_reads = calculate_containment(reads_with_sig, refs_sig)
    plot(containment_with_reads, plot_script_ch)
}

workflow.onComplete {
    println "Workflow completed successfully!"
}