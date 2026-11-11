Name:		junit-bom
Version:	6.0.3
Release:	1
Summary:	JUnit bill of materials for 6.0.3 and 5.12.2
Group:		Development/Java
License:	EPL-2.0
URL:		https://junit.org/junit5/
# Tags r6.0.3 and r5.12.2 of junit-team/junit-framework.
# The archive keeps the Gradle files that name the managed modules.
# Wrapper jars are not included.
Source0:	junit-bom-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	javapackages-filesystem
BuildRequires:	python
%global bom512 5.12.2
# The file attribute generator only emits the pom-typed coordinate.
# Gradle's catalogs ask for the untyped name at both pins.
Provides:	mvn(org.junit:junit-bom) = %{version}
Provides:	mvn(org.junit:junit-bom) = %{bom512}

%description
Bill of materials for JUnit %{version} and %{bom512}. Gradle 9.9.1
imports org.junit:junit-bom at both pins. Platform modules in
%{bom512} stay at 1.12.2. junit-platform-console-standalone is not
a managed dependency. The two POMs are versioned side by side.

%prep
%autosetup -n junit-bom-%{version}
find . -type f \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -print > binaries.list
find . -type d -name '*.jar' -print >> binaries.list
if [ -s binaries.list ]; then
	cat binaries.list
	exit 1
fi

%build
python - <<'PY'
import re
from pathlib import Path


def props_of(path):
    props = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key.startswith("-"):
            continue
        props[key] = value.strip()
    return props


def section(text, name):
    match = re.search(
        rf"^val {name} by extra\((.*?)^(?:val |\Z)",
        text,
        re.S | re.M,
    )
    if not match:
        raise SystemExit("missing " + name)
    return match.group(1)


def artifacts(build_text, includes, name):
    found = []
    for ident in re.findall(r"projects\.(\w+)", section(build_text, name)):
        norm = ident.lower()
        hit = None
        for inc in includes:
            if inc.replace("-", "").lower() == norm:
                hit = inc
                break
        if hit is None:
            raise SystemExit("unmapped " + ident)
        found.append(hit)
    return found


def group_for(kind, pub, props):
    key = kind + "Group"
    if re.search(r'property\("' + key + r'"\)', pub) and key in props:
        return props[key]
    match = re.search(r'in ' + kind + r'Projects -> "([^"]+)"', pub)
    if match:
        return match.group(1)
    raise SystemExit("no group for " + kind)


def bom_group(props, build_text):
    group = props.get("group", "")
    if group.startswith("org."):
        return group
    match = re.search(r'^group = "([^"]+)"', build_text, re.M)
    if not match:
        raise SystemExit("no bom group")
    return match.group(1)


def excluded(bom_text):
    match = re.search(r'it\.name != "([^"]+)"', bom_text)
    if not match:
        raise SystemExit("no standalone filter")
    return match.group(1)


def version_for(kind, pub, props):
    key = kind + "Version"
    if re.search(r'property\("' + key + r'"\)', pub) and key in props:
        return props[key]
    return props["version"]


def description_of(build_text):
    match = re.search(r'^description = "([^"]+)"', build_text, re.M)
    if not match:
        raise SystemExit("no description")
    return match.group(1)


def write_pom(tree, expect_version, dest):
    tree = Path(tree)
    build_text = (tree / "build.gradle.kts").read_text(encoding="utf-8")
    settings = (tree / "settings.gradle.kts").read_text(encoding="utf-8")
    pub = (tree / "publishing-conventions.gradle.kts").read_text(encoding="utf-8")
    bom_text = (tree / "junit-bom.gradle.kts").read_text(encoding="utf-8")
    props = props_of(tree / "gradle.properties")
    includes = re.findall(r'include\("([^"]+)"\)', settings)
    drop = excluded(bom_text)
    rows = []
    for kind, valname in (
        ("jupiter", "jupiterProjects"),
        ("platform", "platformProjects"),
        ("vintage", "vintageProjects"),
    ):
        group = group_for(kind, pub, props)
        version = version_for(kind, pub, props)
        for art in artifacts(build_text, includes, valname):
            if art == drop:
                continue
            rows.append((group, art, version))
    rows.sort(key=lambda row: row[1])
    version = props["version"]
    if version != expect_version:
        raise SystemExit("version " + version + " != " + expect_version)
    group = bom_group(props, build_text)
    name = description_of(build_text) + " (Bill of Materials)"
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<project xmlns="http://maven.apache.org/POM/4.0.0">',
        "  <modelVersion>4.0.0</modelVersion>",
        "  <groupId>" + group + "</groupId>",
        "  <artifactId>junit-bom</artifactId>",
        "  <version>" + version + "</version>",
        "  <packaging>pom</packaging>",
        "  <name>" + name + "</name>",
        "  <description>This Bill of Materials POM can be used to ease dependency management when referencing multiple JUnit artifacts using Gradle or Maven.</description>",
        "  <url>https://junit.org/</url>",
        "  <dependencyManagement>",
        "    <dependencies>",
    ]
    for dep_group, art, dep_version in rows:
        lines.extend([
            "      <dependency>",
            "        <groupId>" + dep_group + "</groupId>",
            "        <artifactId>" + art + "</artifactId>",
            "        <version>" + dep_version + "</version>",
            "      </dependency>",
        ])
    lines.extend([
        "    </dependencies>",
        "  </dependencyManagement>",
        "</project>",
        "",
    ])
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines), encoding="utf-8")
    return rows


write_pom("6.0.3", "%{version}", "pom/junit-bom-%{version}.pom")
write_pom("5.12.2", "%{bom512}", "pom/junit-bom-%{bom512}.pom")
PY

%install
set -eo pipefail
: > .mfiles
pin_bom() {
	ver=$1
	sysjar install --buildroot %{buildroot} \
		--artifact "pom/junit-bom-${ver}.pom" \
		--file-name "junit-bom-${ver}" \
		--filelist ".mfiles-${ver}"
	index="%{buildroot}/usr/share/sysjar/index/org.junit/junit-bom@pom.sysjar"
	test -f "$index"
	/bin/mv "$index" "%{buildroot}/usr/share/sysjar/index/org.junit/junit-bom-${ver}@pom.sysjar"
	sed -i "s|/usr/share/sysjar/index/org.junit/junit-bom@pom\\.sysjar|/usr/share/sysjar/index/org.junit/junit-bom-${ver}@pom.sysjar|" ".mfiles-${ver}"
	grep -F -q "\"version\": \"${ver}\"" "%{buildroot}/usr/share/sysjar/index/org.junit/junit-bom-${ver}@pom.sysjar"
	while IFS= read -r line; do
		grep -qxF -- "$line" .mfiles || printf '%s\n' "$line" >> .mfiles
	done < ".mfiles-${ver}"
}
pin_bom %{version}
pin_bom %{bom512}
if grep -E -q '/junit-bom@pom\.sysjar$' .mfiles; then
	exit 1
fi

%check
python - <<'PY'
import xml.etree.ElementTree as ET
NS = {"m": "http://maven.apache.org/POM/4.0.0"}

def load(path):
    root = ET.parse(path).getroot()
    ver = root.find("m:version", NS).text
    art = root.find("m:artifactId", NS).text
    group = root.find("m:groupId", NS).text
    packaging = root.find("m:packaging", NS).text
    items = {}
    for dep in root.findall("m:dependencyManagement/m:dependencies/m:dependency", NS):
        items[dep.find("m:artifactId", NS).text] = (
            dep.find("m:groupId", NS).text,
            dep.find("m:version", NS).text,
        )
    return group, art, packaging, ver, items

def expect(path, bom_ver, jupiter_ver, platform_ver, count, jfr):
    group, art, packaging, ver, items = load(path)
    if (group, art, packaging, ver) != ("org.junit", "junit-bom", "pom", bom_ver):
        raise SystemExit("bad identity " + path)
    if len(items) != count:
        raise SystemExit("bad count " + ver + " " + str(len(items)))
    if items.get("junit-jupiter") != ("org.junit.jupiter", jupiter_ver):
        raise SystemExit("bad jupiter " + ver)
    if items.get("junit-platform-commons") != ("org.junit.platform", platform_ver):
        raise SystemExit("bad platform " + ver)
    if items.get("junit-platform-launcher") != ("org.junit.platform", platform_ver):
        raise SystemExit("bad launcher " + ver)
    if items.get("junit-vintage-engine") != ("org.junit.vintage", jupiter_ver):
        raise SystemExit("bad vintage " + ver)
    if "junit-platform-console-standalone" in items:
        raise SystemExit("standalone leaked " + ver)
    if jfr and "junit-platform-jfr" not in items:
        raise SystemExit("jfr missing " + ver)
    if (not jfr) and "junit-platform-jfr" in items:
        raise SystemExit("jfr leaked " + ver)
    if jfr and items["junit-platform-jfr"] != ("org.junit.platform", platform_ver):
        raise SystemExit("bad jfr " + ver)
    print("junit_bom_ok", ver, "jupiter", jupiter_ver, "platform", platform_ver, "deps", count)

expect(
    "%{buildroot}/usr/share/maven-poms/junit-bom-%{version}.pom",
    "%{version}", "%{version}", "%{version}", 15, False,
)
expect(
    "%{buildroot}/usr/share/maven-poms/junit-bom-%{bom512}.pom",
    "%{bom512}", "%{bom512}", "1.12.2", 18, True,
)
PY

%files -f .mfiles
%doc LICENSE.md
