Name:           nvidia-driver
Version:        0.0.1
Release:        1%{?dist}
Summary:        A fake nvidia driver RPM package
License:        Public Domain
BuildArch:      noarch

%define _rpmdir ./
%define _rpmfilename mock-%%{NAME}.rpm

%description
A simple dummy package containing one file.

%install
mkdir -p %{buildroot}/usr/bin
echo "#!/bin/sh" > %{buildroot}/usr/bin/nvidia-smi
echo "echo 'This is a mock version of nvidia-smi'" >> %{buildroot}/usr/bin/nvidia-smi
chmod a+x %{buildroot}/usr/bin/nvidia-smi

%files
/usr/bin/nvidia-smi

%changelog
* $(date +"%a %b %d %Y") - 0.0.1-1
- Initial release
