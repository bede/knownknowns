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

- `refs.sig` - Sourmash signatures for references
- `reads.sig` - Sourmash signature for reads
- `containment.csv` - Containment analysis results
- `containment.png` - Bar chart

**Example plot**
![Example containment.png](containment.png "Example containment.png")
