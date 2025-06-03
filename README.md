# Knownknowns

> [there are known knowns; there are things we know we know](https://en.wikipedia.org/wiki/There_are_unknown_unknowns)

A simple workflow for quickly estimating a FASTQ's containment of target genomes using Sourmash. Useful for validating spike-in positive controls. Plots and outputs containment values in CSV format.

## Requirements

- Nextflow (>= 22.0)
- Conda or Docker

## Usage

### Default (conda)

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz \
```

### Docker profile

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz \
    -profile docker
```

## Outputs

- `containment.csv` - Containment results
- `containment.png` - Bar chart of containment by ref sequence

**Example plot**
![Example containment.png](containment.png "Example containment.png")
