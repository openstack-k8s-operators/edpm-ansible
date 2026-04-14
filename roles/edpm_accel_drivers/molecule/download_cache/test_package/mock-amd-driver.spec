Name:           amd-driver
Version:        0.0.1
Release:        1%{?dist}
Summary:        Mock AMD driver RPM package
License:        Public Domain
BuildArch:      noarch

%define _rpmdir ./
%define _rpmfilename mock-%%{NAME}.rpm

%description
A simple dummy package containing one file.

%install
mkdir -p %{buildroot}/usr/local/bin
echo "#!/bin/sh" > %{buildroot}/usr/local/bin/amd-smi
echo "echo 'This is a mock version of amd-smi'" >> %{buildroot}/usr/local/bin/amd-smi
chmod a+x %{buildroot}/usr/local/bin/amd-smi

%files
/usr/local/bin/amd-smi

%changelog
* $(date +"%a %b %d %Y") - 0.0.1-1
- Mock AMD driver RPM package for testing
