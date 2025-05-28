# Knownknowns

> there are known knowns; there are things we know we know

A simple workflow for quickly estimating the containment of one or more genomes in a FASTQ file using Sourmash. Plots and outputs containment values in CSV format.

## Requirements

- Nextflow (>= 22.0)
- Conda or Docker

## Usage

### Default (conda)

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz \
    --outdir results
```

### Docker profile

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz \
    --outdir results \
    -profile docker
```

## Outputs

The workflow generates the following outputs in the specified output directory:

- `refs.sig` - Sourmash signature file for references
- `reads.sig` - Sourmash signature file for reads
- `containment.csv` - Containment analysis results
- `containment.png` - Bar chart visualization (2x resolution)

**Example plot**
![Example containment.png](containment.png "Example containment.png")
