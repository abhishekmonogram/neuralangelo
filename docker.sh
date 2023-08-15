#! /bin/sh

how_to_use() 
{
    echo "How To Use:"
    echo "  -h          Help"
    echo "  -b          Build docker before running"
    echo "  -n          Open new terminal with same docker container"
    exit 1
}

SHOULD_BUILD_BASE=false
IS_NEW_TERMINAL=false
IS_GPU_SET=true
GRAPHICS_ENGINE="gpu"
while getopts ":hbn:" opt; do
    case ${opt} in
        h )
            how_to_use
            ;;
        b )
            SHOULD_BUILD_BASE=true
            echo "here"
            ;;
        n )
            IS_NEW_TERMINAL=true
            ;;
    esac
done

rm .env
echo GPU=nvidia >> .env
echo GPU_VISIBLE=all >> .env
echo GPU_CAPABILITIES=all >> .env
echo GRAPHICS_ENGINE=${GRAPHICS_ENGINE} >> .env

if ${SHOULD_BUILD_BASE} ; then
    docker-compose build build-neuralangelo-base
fi

xhost +SI:localuser:root

if ${IS_NEW_TERMINAL} ; then
    docker-compose -f docker-compose.yml exec develop-container-neuralangelo bash
else
    #docker pull chenhsuanlin/neuralangelo:23.04-py3
    docker-compose -f docker-compose.yml down -v
    docker-compose -f docker-compose.yml up -d develop-container-neuralangelo
    docker-compose -f docker-compose.yml exec develop-container-neuralangelo bash
fi