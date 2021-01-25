# DeePaC-Live
A DeePaC plugin for real-time analysis of Illumina sequencing runs. Captures HiLive2 output and uses deep neural nets to
 detect novel pathogens directly from NGS reads. 
 
We recommend having a look at:

* DeePaC main repo: https://gitlab.com/dacs-hpi/deepac
    * tutorial
    * original bacterial and viral datasets
    * code and documentation

* HiLive2 repo: https://gitlab.com/rki_bioinformatics/HiLive2.
    * extensive tutorial
    * code and documentation

## DeePaC-Live models
DeePaC-Live ships new, updated models for bacterial pathogenic potential and viral infectious potential prediction.
The Illumina models are trained on 25-250bp subreads to ensure high performance over the whole sequencing run. 
The Nanopore models are trained on 250bp subreads corresponding to just around 0.5s of sequencing.
To fetch the models, install DeePaC or DeePaC-Live and use `deepac getmodels --fetch`. In the created directory, you will find the following models ready for inference:

* illu-bac-res18.h5 : an Illumina bacterial model
* illu-vir-res18.h5 : an Illumina viral model
* nano-bac-res18.h5 : a Nanopore bacterial model
* illu-vir-res18.h5 : a Nanopore viral model
  
## Installation

We recommend using Bioconda (based on the `conda` package manager) or custom Docker images based on official Tensorflow images.
Alternatively, a `pip` installation is possible as well. 

### With Bioconda (recommended)
 [![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg?style=flat)](http://bioconda.github.io/recipes/deepaclive/README.html)
 
You can install DeePaC-Live with `bioconda`. Set up the [bioconda channel](
<https://bioconda.github.io/user/install.html#set-up-channels>) first (channel ordering is important):

```
conda config --add channels defaults
conda config --add channels bioconda
conda config --add channels conda-forge
```

We recommend setting up an isolated `conda` environment:
```
# python 3.6, 3.7 and 3.8 are supported
conda create -n my_env python=3.8
conda activate my_env
```

and then:
```
# For GPU support (recommended)
conda install tensorflow-gpu deepaclive
# Basic installation (CPU-only)
conda install deepaclive
```

Highly recommended: download and compile the latest deepac-live custom models:
```
deepac getmodels --fetch
```

If you want to install the DeePaC plugins as well (not necessary), use:
```
#Note: those models were not designed for reads shorter than 250bp. Performance may be unstable.
conda install deepacvir deepacstrain
```

### With Docker (also recommended)

Requirements: 
* install [Docker](https://docs.docker.com/get-docker/) on your host machine. 
* For GPU support, you have to install the [NVIDIA Docker support](https://github.com/NVIDIA/nvidia-docker) as well.

See [TF Docker installation guide](https://www.tensorflow.org/install/docker) and the 
[NVIDIA Docker support installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker) 
for details. The guide below assumes you have Docker 19.03 or above.

You can then pull the desired image:
```
# Basic installation - CPU only
docker pull dacshpi/deepaclive:0.3.2 

# For GPU support
docker pull dacshpi/deepaclive:0.3.2-gpu 
```

And run it:
```
# Basic installation - CPU only
docker run -v $(pwd):/deepac -u $(id -u):$(id -g) --rm dacshpi/deepaclive:0.3.2-gpu deepac-live --help
docker run -v $(pwd):/deepac -u $(id -u):$(id -g) --rm dacshpi/deepaclive:0.3.2-gpu deepac-live test

# With GPU support
docker run -v $(pwd):/deepac -u $(id -u):$(id -g) --rm --gpus all dacshpi/deepaclive:0.3.2-gpu deepac-live test

# If you want to use the shell inside the container
docker run -it -v $(pwd):/deepac -u $(id -u):$(id -g) --rm --gpus all dacshpi/deepaclive:0.3.2-gpu bash
```

The image ships `deepaclive` and the main `deepac` package along the `deepac-vir` and `deepac-strain` plugins. See the basic usage guide below for more deepaclive commands.

Optional: download and compile the latest deepac-live custom models:
```
docker run -v $(pwd):/deepac -u $(id -u):$(id -g) --rm --gpus all dacshpi/deepaclive:0.3.2-gpu deepac --fetch
```

For more information about the usage of the NVIDIA container toolkit (e.g. selecting the GPUs to use),
 consult the [User Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/user-guide.html#user-guide).

The `dacshpi/deepaclive:latest` corresponds to the latest version of the CPU build. We recommend using explicit version tags instead.

### With pip

We recommend setting up an isolated `conda` environment (see above). Alternatively, you can use a `virtualenv` virtual environment (note that deepac requires python 3):
```
# use -p to use the desired python interpreter (python 3.6 or higher required)
virtualenv -p /usr/bin/python3 my_env
source my_env/bin/activate
```

You can then install DeePaC with `pip`. For GPU support, you need to install CUDA and CuDNN manually first (see TensorFlow installation guide for details). 
Then you can do the same as above:

```
pip install deepaclive
```

Optional: download and compile the latest deepac-live custom models:
```
deepac getmodels --fetch
```

If you want to install the DeePaC plugins as well (not necessary), use:
```
#Note: those models were not designed for reads shorter than 250bp. Performance may be unstable.
pip install deepacvir deepacstrain
```

## Basic usage
```
# Run locally: deepac-live Illumina models
deepac-live local -C -m illu-bac-res18.h5 -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined
deepac-live local -C -m illu-vir-res18.h5 -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined

# Run locally: custom model
deepac-live local -C -m custom_model.h5 -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined

# Run locally: built-in model for bacteria (not recommended)
deepac-live local -c deepac -m rapid -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined
# Run locally: built-in model for viruses (not recommended)
deepac-live local -c deepacvir -m rapid -s 25,50,75,100,133,158,183,208 -l 100 -i hilive-out -o temp -I temp -O output -B ACAG-TCGA,undetermined
```

## Advanced usage
### Setting up a remote receiver
```
# Setup sender on the source machine
deepac-live sender -s 25,50,75,100,133,158,183,208 -l 100 -A -i hilive-out -o temp -r user@remote.host:~/rem-temp -k privatekey -B ACAG-TCGA,undetermined
# Setup receiver on the target machine
deepac-live receiver -C -m illu-vir-res18.h5 -m rapid -s 25,50,75,100,133,158,183,208 -l 100 -I rem-temp -O output -B ACAG-TCGA,undetermined
```

### Refilter: ensembles and alternative thresholds
```
# Setup an ensemble on the target machine
deepac-live refilter -s 25,50,75,100,133,158,183,208 -l 100 -i rem-temp -I output_1,output_2 -O final_output -B ACAG-TCGA,undetermined
# Use another threshold
deepac-live refilter -s 25,50,75,100,133,158,183,208 -l 100 -i rem-temp -I output_1 -O final_output -t 0.75 -B ACAG-TCGA,undetermined
```
## Supplementary data and scripts
Datasets are available here: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.4456857.svg)](https://doi.org/10.5281/zenodo.4456857).
You can find the scripts and data files used in the paper for dataset preprocessing and benchmarking [here]( 
https://gitlab.com/dacs-hpi/deepac/-/tree/master/supplement_paper/subreads).

## Known issues
See https://gitlab.com/dacs-hpi/deepac.