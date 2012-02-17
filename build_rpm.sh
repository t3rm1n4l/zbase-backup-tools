#!/bin/bash
#Description: RPM Build script

if [ $1 = "release" ];
then
    specfile=specs/membase-backup-tools-HEAD.spec
    VERSION=`grep Version $specfile | awk '{ print $NF }'`
    RELEASE=`grep Release $specfile | awk '{ print $NF }'`
    COMMIT="$VERSION-$RELEASE"
else
    specfile=specs/membase-backup-tools-template.spec
    VERSION=`git tag | head -1`
    RELEASE=`git log --oneline $VERSION.. | wc -l`
    COMMIT=`git describe`
fi

RPM_SOURCE_DIR=`rpm --eval '%{_sourcedir}'`
SOURCE="membase-backup-tools-$VERSION.tar.gz"
mkdir -p $RPM_SOURCE_DIR
cp $specfile tmp-$$.spec
sed -i "s/_VERSION/$VERSION/" tmp-$$.spec
sed -i "s/_SOURCE/$SOURCE/" tmp-$$.spec
sed -i "s/_RELEASE/$RELEASE/" tmp-$$.spec
sed -i "s/_COMMIT/$COMMIT/" tmp-$$.spec
git archive --format=tar --prefix="membase-backup-tools-$VERSION/" HEAD | gzip > $RPM_SOURCE_DIR/$SOURCE
rpmbuild -ba tmp-$$.spec
rm tmp-$$.spec
