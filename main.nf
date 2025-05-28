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
    publishDir "${params.outdir}", mode: 'copy'

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
    publishDir "${params.outdir}", mode: 'copy'

    conda 'bioconda::sourmash'

    input:
    path reads

    output:
    path "reads.sig"

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
    publishDir "${params.outdir}", mode: 'copy'

    conda 'bioconda::sourmash'

    input:
    path reads_sig
    path refs_sig

    output:
    path "containment.csv"

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

process create_visualization {
    tag "visualization"
    publishDir "${params.outdir}", mode: 'copy'

    conda 'conda-forge::altair conda-forge::pandas conda-forge::vl-convert-python'

    input:
    path containment_csv
    path plot_script

    output:
    path "containment.png", optional: true
    path "containment.csv"

    script:
    """
    mamba install -y -c conda-forge altair pandas vl-convert-python
    python ${plot_script} ${containment_csv} \\
        --output-plot containment.png \\
        --output-csv containment.csv \\
        --debug
    """
}

workflow {
    references_ch = Channel.fromPath(params.references, checkIfExists: true)
    reads_ch = Channel.fromPath(params.reads, checkIfExists: true)
    plot_script_ch = Channel.fromPath("$projectDir/plot_containment.py", checkIfExists: true)
    refs_sig = sketch_references(references_ch)
    reads_sig = sketch_reads(reads_ch)
    containment_csv = calculate_containment(reads_sig, refs_sig)
    create_visualization(containment_csv, plot_script_ch)
}

workflow.onComplete {
    println "Workflow completed successfully!"
    println "Results are available in: ${params.outdir}"
    println "- refs.sig: Reference sketches"
    println "- reads.sig: Reads sketches"
    println "- containment.csv: Containment analysis results"
    println "- containment.png: Visualization (2x resolution)"
}