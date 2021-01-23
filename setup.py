from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()


setup(name='deepaclive',
      version='0.3.1',
      description='Detecting novel pathogens from NGS reads in real-time during a sequencing run.',
      long_description=readme(),
      long_description_content_type='text/markdown',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
      ],
      keywords='deep learning DNA sequencing synthetic biology pathogenicity prediction',
      url='https://gitlab.com/dacs-hpi/deepac-live',
      author='Jakub Bartoszewicz',
      author_email='jakub.bartoszewicz@hpi.de',
      license='MIT',
      packages=['deepaclive'],
      python_requires='>=3',
      install_requires=[
          'deepac>=0.12.0',
          'tensorflow>=2.1',
          'pysam>=0.15.4',
          'paramiko>=2.7.1',
          'scikit-learn>=0.22.1',
          'numpy>=1.18.1',
          'biopython>=1.76'
      ],
      entry_points={
          'console_scripts': ['deepac-live=deepaclive.command_line:main'],
      },
      include_package_data=True,
      zip_safe=False)
