
from setuptools import setup, find_packages


setup(
    name='tdw_physics',
    version="0.3.2",
    description='Generic structure to create physics datasets with TDW.',
    long_description="Required Python scripts for TDW.",
    url='https://github.com/alters-mit/tdw_physics',
    author='Seth Alter',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8'
    ],
    keywords='unity simulation tdw hdf5',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=['tqdm', 'numpy', 'h5py', 'pillow', 'weighted-collection', 'tdw'],
)
