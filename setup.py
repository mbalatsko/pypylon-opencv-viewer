import os
from setuptools import find_packages, setup

os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open('README.md') as f:
    long_description = f.read()

setup(
    name='pypylon-opencv-viewer',
    packages=find_packages(),
    version='1.0',
    description='Easy to use Jupyter notebook interface connecting Basler Pylon images grabbing with openCV image processing.'
    ' Allows to specify interactive Jupyter widgets to manipulate Basler camera features values, grab camera image and at'
    'once get an OpenCV window on which raw camera output is displayed or you can specify an image processing function,'
    'which takes on the input raw camera output image and display your own output.',
	long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT License',
    author='Maksym Balatsko',
    author_email='mbalatsko@gmail.com',
    url='https://github.com/mbalatsko/pypylon-opencv-viewer',
    download_url='https://github.com/mbalatsko/pypylon-opencv-viewer/archive/1.0.tar.gz',
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