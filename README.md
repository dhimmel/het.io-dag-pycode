# Python Code for Hetio Disease-Gene Prediction Study

This repository contains Python code for the study:

> **Heterogeneous Network Edge Prediction: A Data Integration Approach to Prioritize Disease-Associated Genes**  
Daniel S. Himmelstein, Sergio E. Baranzini  
*PLOS Computational Biology* (2015-07-09) <https://doi.org/98q>  
DOI: [10.1371/journal.pcbi.1004259](https://doi.org/10.1371/journal.pcbi.1004259) · PMID: [26158728](https://www.ncbi.nlm.nih.gov/pubmed/26158728) · PMCID: [PMC4497619](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4497619)

## History

This repository originally used mercurial and was hosted on BitBucket at `https://bitbucket.org/dhimmel/rhetio`.
Unfortunately, BitBucket [deleted](https://community.atlassian.com/t5/Bitbucket-articles/What-to-do-with-your-Mercurial-repos-when-Bitbucket-sunsets/ba-p/1155380) mercurial repos in 2020 without an automated migration path.
On 2020-09-10, dhimmel realized this source code was no longer online.

The repo could not be retrieved from BitBucket, but dhimmel had a local copy in `~/Documents/serg/gene-disease-hetnet/pyhetio`.
Using the [hg-git](https://hg-git.github.io/) mercurial plugin, dhimmel pushed the repo to <https://github.com/dhimmel/het.io-dag-pycode>.

The extent this python code was used to extract the network-based features for the study is unknown.
It's uploaded to GitHub for archiving and historical purposes.
This code predates the dedicated hetnetpy Python package at https://github.com/hetio/hetnetpy.
Much of this codebase was migrated to that project.
