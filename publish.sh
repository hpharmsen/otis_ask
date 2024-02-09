export VERSION=`python bumpversion.py -v patch`
echo $VERSION
git commit -v -a -m "publish `date`"
git tag -a $VERSION -m "version $VERSION"
git push origin $VERSION
echo "run:"
echo "pip install git+https://github.com/hpharmsen/otis_ask@$VERSION"
