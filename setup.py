from setuptools import setup, find_packages

long_description = '''
This project is a tool to prepare investment data for tax reporting
'''

version = "1.0.0"

requirements = [
]

if __name__ == '__main__':
    setup(
        name="shares-reporting",
        version="0.0.1",
        py_modules=["config", "extraction", "domain", "reporting", "persisting","transformation"],
        url="http://github.com/bes-shutok/shares",
        author="Andrey Dmitriev",
        author_email="dmitriev.andrey.vitalyevich@gmail.com",
        description="Shares reporting tool",
        long_description=long_description,
        long_description_content_type="text/markdown",
        packages=find_packages(
            exclude=[
                'tests',
            ],
            include=[
                'scripts',
                'utils'
            ],
        ),
        license='MIT',
        install_requires=requirements,
        classifiers=[
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Development Status :: 4 - Beta",
            "Environment :: Other Environment",
            "Intended Audience :: Developers",
            "Operating System :: OS Independent",
            "Topic :: Software Development :: Libraries :: Python Modules"
          ],
        )