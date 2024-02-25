from setuptools import setup

VERSION = "0.0.20"

requirements = open("requirements.txt").readlines()

if __name__ == "__main__":
    setup(
        name='gpt-pilot',
        version=VERSION,
        packages=['pilot'],
        url='https://www.pythagora.ai',
        license='MIT',
        author_email='info@pythagora.ai',
        description='GPT Pilot - an AI developer that works with you to build complex projects',
        long_description=open('README.md').read(),
        long_description_content_type='text/markdown',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 3',
        ],
        install_requires=requirements,
        python_requires='>=3.9',
    )
