from setuptools import (
    find_packages,
    setup
)


package_name = 'stirrups'
version = '0.1.3'
url = 'https://github.com/cbourget/stirrups'

install_requires = []

extras_require = {
    'tests': [
        'pytest',
        'coverage',
        'pytest-cov'
    ]
}


setup(
    name=package_name,
    version=version,
    author='Charles-Eric Bourget',
    author_email='charlesericbourget@gmail.com',
    description='Dependency injection library',
    long_description=open('README.rst').read(),
    license='MIT',
    url=url,
    download_url='{}/archive/{}.tar.gz'.format(url, version),
    keywords='dependency injection',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    install_requires=install_requires,
    extras_require=extras_require
)
