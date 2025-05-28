#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

// Parameters
params.references = null
params.reads = null
params.outdir = "results"

// Input validation
if (!params.references) {
    error "Please provide a references file with --references"
}
if (!params.reads) {
    error "Please provide a reads file with --reads"
}

// Process to sketch reference sequences
process SKETCH_REFERENCES {
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

// Process to sketch reads
process SKETCH_READS {
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

// Process to calculate containment scores
process CALCULATE_CONTAINMENT {
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
    sourmash search \\
        --max-containment \\
        -t 0.0 \\
        -o containment.csv \\
        ${reads_sig} \\
        ${refs_sig}
    """
}

// Process to create visualization
process CREATE_VISUALIZATION {
    tag "visualization"
    publishDir "${params.outdir}", mode: 'copy'
    
    conda 'conda-forge::altair conda-forge::pandas conda-forge::vl-convert-python'
    
    input:
    path containment_csv
    
    output:
    path "containment_plot.png"
    path "containment.csv"
    
    script:
    """
    #!/usr/bin/env python3
    
    import pandas as pd
    import altair as alt
    
    # Enable PNG export with vl-convert
    alt.data_transformers.enable('json')
    
    # Read the containment data
    df = pd.read_csv('${containment_csv}')
    
    # Create the Altair chart
    chart = alt.Chart(df).mark_bar(size=8).encode(
        y=alt.Y('name:N', title="Reference Sequence", sort='-x'),
        x=alt.X('similarity:Q', title="Containment Score", scale=alt.Scale(domain=[0, 1])),
        tooltip=['name:N', 'similarity:Q', 'md5:N']
    ).properties(
        width=600,
        height=alt.Step(20),
        title="Sourmash Containment Analysis"
    ).resolve_scale(
        y='independent'
    )
    
    # Save as PNG with 2x resolution using vl-convert
    chart.save('containment_plot.png', scale_factor=2.0)
    
    # Copy the CSV file to output
    df.to_csv('containment.csv', index=False)
    
    print(f"Created visualization with {len(df)} reference sequences")
    print(f"Containment scores range: {df['similarity'].min():.3f} - {df['similarity'].max():.3f}")
    """
}

// Main workflow
workflow {
    // Create input channels
    references_ch = Channel.fromPath(params.references, checkIfExists: true)
    reads_ch = Channel.fromPath(params.reads, checkIfExists: true)
    
    // Execute processes
    refs_sig = SKETCH_REFERENCES(references_ch)
    reads_sig = SKETCH_READS(reads_ch)
    containment_csv = CALCULATE_CONTAINMENT(reads_sig, refs_sig)
    CREATE_VISUALIZATION(containment_csv)
}

workflow.onComplete {
    println "Workflow completed successfully!"
    println "Results are available in: ${params.outdir}"
    println "- refs.sig: Reference sketches"
    println "- reads.sig: Reads sketches" 
    println "- containment.csv: Containment analysis results"
    println "- containment_plot.png: Visualization (2x resolution)"
}