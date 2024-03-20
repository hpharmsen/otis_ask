export VERSION=`python bumpversion.py -v patch`
echo $VERSION
git commit -v -a -m "publish `date`"
git tag -a $VERSION -m "version $VERSION"
git push origin $VERSION
echo "run:"
echo "python -m pip install  otis_ask@git+https://github.com/hpharmsen/otis_ask.git@$VERSION"