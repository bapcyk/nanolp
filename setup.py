from distutils.core import setup
from distutils.command.build_py import build_py
#from distutils.command.install_scripts import install_scripts
from distutils.command.install import install
from glob import glob
import shutil
import sys

_PY23 = 3 if sys.version_info.major > 2 else 2

class build_py23(build_py):
    """Different build for Py 2 and Py 3"""
    def find_package_modules(self, package, package_dir):
        modules = build_py.find_package_modules(self, package, package_dir)
        if _PY23 == 3:
            modules = [m for m in modules if 'lpcompat2' not in m[1]]
        else:
            modules = [m for m in modules if 'lpcompat3' not in m[1]]
        return modules

class log_install(install):
    """Logging of all installed paths what is used in tests or elsewhere"""
    def finalize_options(self):
        install.finalize_options(self)
        installation_log = \
'''# Installation paths log
SCRIPTS_DIR = r'{SCRIPTS_DIR}'
PURELIB_DIR = r'{PURELIB_DIR}'
DATA_DIR = r'{DATA_DIR}'
'''
        log = dict(
                SCRIPTS_DIR=self.install_scripts,
                PURELIB_DIR=self.install_purelib,
                DATA_DIR=self.install_data,
        )
        for v in log.values():
            if not v: raise RuntimeError('Can not log installation paths!')
        installation_log = installation_log.format(**log)
        with open('nanolp/_instlog.py', 'wt') as f:
            f.write(installation_log)

cmd_class = dict(
    build_py = build_py23,
    install = log_install
) 

shutil.rmtree('build', True)
setup(name="nanolp",
    version="1.0",
    description="Literate Programming Tool",
    long_description = open('README.txt').read(),
    author="Pavel Y",
    author_email="aquagnu@gmail.com",
    url='http://code.google.com/p/nano-lp/',
    download_url='http://nano-lp.googlecode.com/files/nanolp-1.0.zip',
    packages = ["nanolp", "nanolp.test"],
    package_data = {"nanolp.test": ["*.zip"]},
    scripts=['bin/nlp.py', 'bin/lprc', 'bin/lpurlrc'],
    data_files = [('nanolp-extra', glob('nanolp-extra/*'))],
    license='GNU GPLv2',
    keywords=['Literate Programming', 'Documentation'],
    classifiers = [
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Environment :: Other Environment',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Topic :: Documentation',
            'Topic :: Scientific/Engineering',
            'Topic :: Software Development :: Documentation',
            'Topic :: Text Processing :: Markup',
            'Topic :: Utilities',
        ],
    cmdclass=cmd_class,
)
