#!/usr/bin/env bash
PROJDIR=`dirname "$0"`
PROJNAME=console
CURDIR=`pwd`
VERSION=$(cat ${PROJDIR}/VERSION 2>&- || echo latest)

createpack() {
    local file=$1/${PROJNAME}_${VERSION}.zip
    if /usr/bin/env python3 -m zipfile -c "$file" "$PROJDIR/$PROJNAME"
    then
        echo -e "Create a package file located in \n\t${file}"
    else
        return 1
    fi
}

cd $PROJDIR

shopt -s globstar
rm -rf ${PROJDIR}/**/__pycache__
if [ $(uname -s) = 'Darwin' ]; then
    rm -rf ${PROJDIR}/**/.DS_store
    rm -rf ${PROJDIR}/**/._*
fi

createpack $CURDIR || createpack $HOME || createpack $PROJDIR || echo Cannot create package file
cd $CURDIR
