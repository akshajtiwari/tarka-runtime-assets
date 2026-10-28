#!/bin/sh
set -eu
cd /workspace
python3 -c 'import ssl, subprocess; print("python-ok", ssl.OPENSSL_VERSION)'
python3 -m venv /home/tarka/venv
/home/tarka/venv/bin/python -m pip --version
git --version
gh --version
cd java
mkdir -p library app
javac -d library Library.java
jar --create --file library.jar -C library .
javac -cp library.jar -d app Main.java
printf 'Main-Class: Main\nClass-Path: library.jar\n' > manifest.mf
jar --create --file app.jar --manifest manifest.mf -C app .
java -jar app.jar
cd ../maven
mvn -B -ntp clean package
mvn -B -ntp -o clean package
java -cp target/classes:/home/tarka/.m2/repository/org/apache/commons/commons-lang3/3.17.0/commons-lang3-3.17.0.jar Main
cd ../gradle
gradle --no-daemon --console=plain clean build run
gradle --no-daemon --console=plain --offline clean build run
cd ../cpp
cmake -S . -B build -G Ninja
cmake --build build
./build/smoke
printf 'all-linux-toolchain-checks-passed\n'
