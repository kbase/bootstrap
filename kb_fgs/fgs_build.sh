#!/bin/sh
set -x

. ../tools/error_handler

trap 'error ${LINENO}' ERR

target=${TARGET-/kb/runtime}

if [[ $# -gt 0 ]] ; then
	target=$1
	shift
fi

rm -rf FGS
git clone https://github.com/wltrimbl/FGS.git

pushd FGS
make
mkdir bin
mv train bin/.
mv *.pl bin/.
mv FragGeneScan bin/.
popd

rm -rf $target/FragGeneScan
mv FGS $target/FragGeneScan
ln -s $target/FragGeneScan/bin/* $target/bin/.
