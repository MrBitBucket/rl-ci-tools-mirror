#from distutils.core import setup
from setuptools import setup
import os, sys

if __name__=='__main__':
    pkgDir=os.path.dirname(sys.argv[0])
    if not pkgDir:
        pkgDir=os.getcwd()
    if not os.path.isabs(pkgDir):
        pkgDir=os.path.abspath(pkgDir)
    sys.path.insert(0,pkgDir)
    os.chdir(pkgDir)
    import rl_ci_tools
    version = rl_ci_tools.VERSION

    setup(name='rl_ci_tools',
        version=version,
        description='Continuous Integration Support for ReportLab and friends',
        author='Robin Becker',
        author_email='andy@reportlab.com',
        url='https://bitbucket.org/MrRLBitBucket/rl_ci_tools',
        py_modules=['rl_ci_tools'],
        requires=['requests'],
        )
