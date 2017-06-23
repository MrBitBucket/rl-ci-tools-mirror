#!/bin/bash
# Run with:
#	 docker run --rm -v $PWD:/io quay.io/pypa/manylinux1_x86_64 /io/build_reportlab.sh
# or something like:
#	 docker run --rm -e PYTHON_VERSIONS=2.7 -v $PWD:/io quay.io/pypa/manylinux1_x86_64 /io/build_reportlab.sh
# or:
#	 docker run --rm -e PYTHON_VERSIONS=2.7 -v $PWD:/io quay.io/pypa/manylinux1_x86_64 /io/build_reportlab.sh
set -e

UNICODE_WIDTHS=${UNICODE_WIDTHS:-16 32}
WHEELHOUSE=${WHEELHOUSE:-/io/wheelhouse}
WHEELS_UNFIXED=${WHEELS_UNFIXED:-/io/wheels_unfixed}

mark(){
	echo "######################################################################################"
	[ "$#" -gt 0 ] && echo "$@" && echo "######################################################################################"
	}

# Manylinux, openblas version, lex_ver etc etc
mark source /io/rl_ci_utils/manylinux/manylinux_utils.sh
source /io/rl_ci_utils/manylinux/manylinux_utils.sh
mark source /io/rl_ci_utils/manylinux/library_builders.sh
source /io/rl_ci_utils/manylinux/library_builders.sh
mark "$(env)"

#mark build_jpeg
#build_jpeg
#mark build_tiff
#build_tiff
#mark build_openjpeg
#build_openjpeg
#mark build_lcsm2
#build_lcms2
#mark build_libwebp
#build_libwebp
#mark build_freetype
#build_freetype
#yum install -y tk-devel

PYLO=${PYLO:-2.7}
PYHI=${PYHI:-3.7}

OPATH="$PATH"
export RL_MANYLINUX=1
ENV=/io/test-env
SRC=/io/${REQUIREMENT}-src

# Compile wheels
for PYTHON in ${PYTHON_VERSIONS}; do
	[ $(lex_ver $PYTHON) -lt $(lex_ver $PYLO) ] && continue
	[ $(lex_ver $PYTHON) -ge $(lex_ver $PYHI) ] && continue
	for uw in ${UNICODE_WIDTHS}; do
		[ $(lex_ver $PYTHON) -ge $(lex_ver 3.3) ] && [ "$uw" != 32 ] && continue
		(
		export UNICODE_WIDTH="$uw"
		mark "building reportlab wheel PYTHON=$PYTHON UNICODE_WIDTH=$UNICODE_WIDTH"
		PP="$(cpython_path $PYTHON $UNICODE_WIDTH)"
		PY=$PP/bin/python
		mark "platform=$($PY -mplatform) sys.platform=$($PY -c'import sys;print(sys.platform)') os.name=$($PY -c'import os;print(os.name)')"
		export PATH="$PP/bin:$OPATH"
		PIP="$PP/bin/pip"
		echo "Testing ${REQUIREMENT} for Python $PYTHON"
		$PIP install virtualenv
		rm -rf $ENV
		$PY -mvirtualenv $ENV
		(
		cd $ENV
		. $ENV/bin/activate
		EPY=$ENV/bin/python
		EPIP=$ENV/bin/pip
		[ "${REQUIREMENT}" = "reportlab" ] && $EPIP install --find-links=/io/TEST-WHEELS pillow
		$EPIP install --find-links=/io/wheels ${REQUIREMENT}
		rm -f /tmp/eee
		$EPY setup.py test | tee /tmp/eee
		grep -q 'OK' /tmp/eee && R="##### OK  " || R="!!!!! FAIL"
		echo "${R} PYTHON=${PYTHON} UNICODE_WIDTH=${UNICODE_WIDTH} ARCH=${ARCH}" >> /io/test-results.txt
		deactivate
		)
		)
	done
done
