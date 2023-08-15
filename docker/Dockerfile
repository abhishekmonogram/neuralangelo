FROM nvcr.io/nvidia/cuda:11.8.0-devel-ubuntu20.04
ARG DEBIAN_FRONTEND=noninteractive

# Install basics
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    bzip2 \
    ca-certificates \
    cmake \
    curl \
    ffmpeg \
    g++ \
    git \
    libx264-dev \
    tmux \
    wget

# colmap dependencies
RUN apt-get update && apt-get install -y \
    ninja-build \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-test-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libsqlite3-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev
# headless servers
RUN apt-get update && apt-get install -y \
    xvfb
# Colmap
RUN git clone https://github.com/colmap/colmap.git && cd colmap && git checkout 3.8
RUN cd colmap && mkdir build && cd build && cmake .. -DCUDA_ENABLED=ON -DCMAKE_CUDA_ARCHITECTURES="70;72;75;80;86" -GNinja
RUN cd colmap/build && ninja && ninja install

COPY --from=nvcr.io/nvidia/pytorch:23.04-py3 /opt/pytorch /opt/pytorch
COPY --from=nvcr.io/nvidia/pytorch:23.04-py3 /usr/local/lib/python3.8/dist-packages/torch /usr/local/lib/python3.8/dist-packages/torch

# additional python packages
RUN apt-get update && apt-get install -y \
    pip \
    ffmpeg
RUN pip install \
    addict \
    opencv-python-headless \
    pillow \
    pyyaml \
    trimesh

# Update pip
RUN pip install --upgrade pip

# Code formatting
RUN pip install --upgrade \
    flake8 \
    pre-commit
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
# Install base Python libraries for Imaginaire
COPY requirements.txt requirements.txt
ARG FORCE_CUDA=1
ARG TCNN_CUDA_ARCHITECTURES=70,72,75,80,86
RUN pip install --upgrade -r requirements.txt
RUN wget --quiet https://repo.anaconda.com/archive/Anaconda3-2023.07-2-Linux-x86_64.sh -O ~/anaconda.sh && \
    /bin/bash ~/anaconda.sh -b -p /opt/conda && \
    rm ~/anaconda.sh && \
    ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
    echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc
COPY . /neuralangelo
RUN cd /neuralangelo && /opt/conda/bin/conda env create --file neuralangelo.yaml && \
    /opt/conda/bin/conda activate neuralangelo


# Last line ------------------------------------------------------------------------------------------------------------