# Knownknowns

> [there are known knowns; there are things we know we know](https://en.wikipedia.org/wiki/There_are_unknown_unknowns)

A workflow for estimating and plotting the containment of sequences in a fasta file (`--references`) for either a single FASTQ file or a directory of FASTQ files (`--reads`). A minimum depth threshold  (`--min_depth`) may be specified, and plots are annotated with estimated depth of coverage. Outputs containment values and abundance estimates in CSV format and plots in PNG format. Specifiy *k*-mer length with `--kmer`  (default 31) and sketch resolution with `--scaled` (default 100).

## Requirements

- Nextflow (>= 22.0)
- Conda or Docker

## Usage

### Minimal

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz
```

### Maximal

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz
    --kmer 31 \
    --scaled 100 \
    --min_depth 1 \
    --plot true
```

### Docker profile (uses conda by default)

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data/mn908947.fastq.gz \
    -profile docker
```

## All options



### Signature input

`--reads` and `--references` both also accept presketched Sourmash sketches (`.sig`) created with `sourmash sketch`

### Multiple FASTQ input

`--reads` can accept either a single `fastq.[gz]` file or a path to a directory containing many `fastq.[gz]` files (one per sample). Both sample-level plots and a combined plot showing containment across samples is generated upon completion.

```bash
nextflow run main.nf \
    --references test/data/mn908947.fa \
    --reads test/data
```

## Outputs

- `containment.csv` - Containment results
- `containment.png` - Bar chart of containment by reference chromosome

**Example plot**
![Example containment.png](containment.png "Example containment.png")
