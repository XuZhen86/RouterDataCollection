import setuptools

setuptools.setup(
    name='router-data-collection',
    version='0.1',
    author='XuZhen86',
    url='https://github.com/XuZhen86/RouterDataCollection',
    packages=setuptools.find_packages(),
    python_requires='==3.11.7',
    install_requires=[
        'absl-py==1.4.0',
        'influxdb-client==1.36.1',
        'line_protocol_cache@git+https://github.com/XuZhen86/LineProtocolCache@65d1270',
    ],
    entry_points={
        'console_scripts': ['router-data-collection = router_data_collection.main:app_run_main',],
    },
)
