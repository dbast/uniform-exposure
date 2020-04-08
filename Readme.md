![Docker Pulls](https://img.shields.io/docker/pulls/dbast/uniform-exposure)
![Docker Cloud Build Status](https://img.shields.io/docker/cloud/build/dbast/uniform-exposure)
![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/dbast/uniform-exposure)
![MicroBadger Layers](https://img.shields.io/microbadger/layers/dbast/uniform-exposure)

Clone of https://bitbucket.org/a1ex/uniform-exposure with Dockerfile + CI

See also https://www.magiclantern.fm/forum/index.php?topic=7022.0

Howto:
* Create a folder called `raw`.
* Put your raw files into the `./raw` folder
* Run uniform_exposure via either:
  * Container from Docker Hub: `docker run --rm -v ${PWD}:/tmp -it dbast/uniform-exposure` or
  * Local container creation: `docker run --rm -v ${PWD}:/tmp -it $(docker build -q .)`
