import os
from setuptools import find_packages, setup

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open('README.md') as f:
    long_description = f.read()

setup(
    name='pypylon-opencv-viewer',
    packages=find_packages(),
    version='1.0.1',
    description='Save on disc added, Get image added',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT License',
    author='Maksym Balatsko',
    author_email='mbalatsko@gmail.com',
    url='https://github.com/mbalatsko/pypylon-opencv-viewer',
    download_url='https://github.com/mbalatsko/pypylon-opencv-viewer/archive/1.0.1.tar.gz',
    install_requires=[
        'opencv-python',
        'jupyter',
        'pypylon',
        'ipywidgets',
        'ipython'
    ],
    keywords=['basler', 'pypylon', 'opencv', 'jypyter', 'pypylon viewer', 'opencv pypylon'],
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent'
    ],
)