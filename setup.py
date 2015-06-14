# setup for pylal


import os
from misc import generate_vcs_info as gvcsi
from distutils.core import setup, Extension
from distutils.command import install
from distutils.command import build
from distutils.command import build_py
from distutils.command import sdist
from distutils import log
import subprocess
import sys
import time
from numpy.lib.utils import get_include as numpy_get_include


#
# check python version
#

if sys.version_info[0] != 2 or sys.version_info[1] < 4:
	log.error("Python version is %s.  pylal requires a Python version such that 2.4 <= version < 3" % sys.version)
	sys.exit(1)


class PkgConfig(object):
	def __init__(self, names):
		def stripfirsttwo(string):
			return string[2:]
		self.libs = map(stripfirsttwo, os.popen("pkg-config --libs-only-l %s" % names).read().split())
		self.libdirs = map(stripfirsttwo, os.popen("pkg-config --libs-only-L %s" % names).read().split())
		self.incdirs = map(stripfirsttwo, os.popen("pkg-config --cflags-only-I %s" % names).read().split())
		self.extra_cflags = os.popen("pkg-config --cflags-only-other %s" % names).read().split()

gsl_pkg_config = PkgConfig("gsl")
lal_pkg_config = PkgConfig("lal")
lalsupport_pkg_config = PkgConfig("lalsupport")
# FIXME:  works for GCC only!!!
lal_pkg_config.extra_cflags += ["-std=c99"]
lalmetaio_pkg_config = PkgConfig("lalmetaio")
lalsimulation_pkg_config = PkgConfig("lalsimulation")
lalinspiral_pkg_config = PkgConfig("lalinspiral")

def remove_root(path, root):
	if root:
		return os.path.normpath(path).replace(os.path.normpath(root), "")
	return os.path.normpath(path)

def write_build_info():
	"""
	Get VCS info from misc/generate_vcs_info.py and add build information.
	Substitute these into misc/git_version.py.in to produce
	pylal/git_version.py.
	"""
	vcs_info = gvcsi.generate_git_version_info()

	# determine current time and treat it as the build time
	build_date = time.strftime('%Y-%m-%d %H:%M:%S +0000', time.gmtime())

	# determine builder
	retcode, builder_name = gvcsi.call_out(('git', 'config', 'user.name'))
	if retcode:
		builder_name = "Unknown User"
	retcode, builder_email = gvcsi.call_out(('git', 'config', 'user.email'))
	if retcode:
		builder_email = ""
	builder = "%s <%s>" % (builder_name, builder_email)

	sed_cmd = ('sed',
		'-e', 's/@ID@/%s/' % vcs_info.id,
		'-e', 's/@DATE@/%s/' % vcs_info.date,
		'-e', 's/@BRANCH@/%s/' % vcs_info.branch,
		'-e', 's/@TAG@/%s/' % vcs_info.tag,
		'-e', 's/@AUTHOR@/%s/' % vcs_info.author,
		'-e', 's/@COMMITTER@/%s/' % vcs_info.committer,
		'-e', 's/@STATUS@/%s/' % vcs_info.status,
		'-e', 's/@BUILDER@/%s/' % builder,
		'-e', 's/@BUILD_DATE@/%s/' % build_date,
		'misc/git_version.py.in')

	# FIXME: subprocess.check_call becomes available in Python 2.5
	sed_retcode = subprocess.call(sed_cmd,
		stdout=open('pylal/git_version.py', 'w'))
	if sed_retcode:
		raise gvcsi.GitInvocationError


class pylal_build_py(build_py.build_py):
	def run(self):
		# If we are building from tarball, do not update git version.
		# PKG-INFO is inserted into the tarball by the sdist target.
		if not os.path.exists("PKG-INFO"):
			# create the git_version module
			try:
				write_build_info()
				log.info("Generated pylal/git_version.py")
			except gvcsi.GitInvocationError:
				if not os.path.exists("pylal/git_version.py"):
					log.error("Not in git checkout or cannot find git executable.")
					sys.exit(1)

		# resume normal build procedure
		build_py.build_py.run(self)

class pylal_install(install.install):
	def run(self):
		pylal_prefix = remove_root(self.prefix, self.root)

		# Hardcode a check for system-wide installation;
		# in this case, don't make the user-env scripts.
		if pylal_prefix == sys.prefix:
			self.distribution.data_files = []
			install.install.run(self)
			return

		# create the user env scripts
		if self.install_purelib == self.install_platlib:
			pylal_pythonpath = self.install_purelib
		else:
			pylal_pythonpath = self.install_platlib + ":" + self.install_purelib

		pylal_install_scripts = remove_root(self.install_scripts, self.root)
		pylal_pythonpath = remove_root(pylal_pythonpath, self.root)
		pylal_install_platlib = remove_root(self.install_platlib, self.root)

		if not os.path.isdir("etc"):
			os.mkdir("etc")
		log.info("creating pylal-user-env.sh script")
		env_file = open(os.path.join("etc", "pylal-user-env.sh"), "w")
		print >> env_file, "# Source this file to access PYLAL"
		print >> env_file, "PYLAL_PREFIX=" + pylal_prefix
		print >> env_file, "export PYLAL_PREFIX"
		if self.distribution.scripts:
			print >> env_file, "PATH=" + pylal_install_scripts + ":${PATH}"
			print >> env_file, "export PATH"
		print >> env_file, "PYTHONPATH=" + pylal_pythonpath + ":${PYTHONPATH}"
		print >> env_file, "LD_LIBRARY_PATH=" + pylal_install_platlib + ":${LD_LIBRARY_PATH}"
		print >> env_file, "DYLD_LIBRARY_PATH=" + pylal_install_platlib + ":${DYLD_LIBRARY_PATH}"
		print >> env_file, "export PYTHONPATH LD_LIBRARY_PATH DYLD_LIBRARY_PATH"
		env_file.close()

		log.info("creating pylal-user-env.csh script")
		env_file = open(os.path.join("etc", "pylal-user-env.csh"), "w")
		print >> env_file, "# Source this file to access PYLAL"
		print >> env_file, "setenv PYLAL_PREFIX " + pylal_prefix
		if self.distribution.scripts:
			print >> env_file, "setenv PATH " + pylal_install_scripts + ":${PATH}"
		print >> env_file, "if ( $?PYTHONPATH ) then"
		print >> env_file, "  setenv PYTHONPATH " + pylal_pythonpath + ":${PYTHONPATH}"
		print >> env_file, "else"
		print >> env_file, "  setenv PYTHONPATH " + pylal_pythonpath
		print >> env_file, "endif"
		print >> env_file, "if ( $?LD_LIBRARY_PATH ) then"
		print >> env_file, "  setenv LD_LIBRARY_PATH " + pylal_install_platlib + ":${LD_LIBRARY_PATH}"
		print >> env_file, "else"
		print >> env_file, "  setenv LD_LIBRARY_PATH " + pylal_install_platlib
		print >> env_file, "endif"
		print >> env_file, "if ( $?DYLD_LIBRARY_PATH ) then"
		print >> env_file, "  setenv DYLD_LIBRARY_PATH " + pylal_install_platlib + ":${DYLD_LIBRARY_PATH}"
		print >> env_file, "else"
		print >> env_file, "  setenv DYLD_LIBRARY_PATH " + pylal_install_platlib
		print >> env_file, "endif"
		env_file.close()

		# now run the installer
		install.install.run(self)

class pylal_sdist(sdist.sdist):
	def run(self):
		# customize tarball contents
		self.distribution.data_files = []
		for root,dirs,files in os.walk("debian"):
			for file in files:
				self.distribution.data_files += [os.path.join(root,file)]
		self.distribution.data_files += ["pylal.spec"]

		# create the git_version module
		try:
			write_build_info()
			log.info("generated pylal/git_version.py")
		except gvcsi.GitInvocationError:
			if not os.path.exists("pylal/git_version.py"):
				log.error("Not in git checkout or cannot find git executable. Exiting.")
				sys.exit(1)

		# now run sdist
		sdist.sdist.run(self)

# FIXME:  all occurances of -DPY_SSIZE_T_CLEAN are a temporary hack to
# induce PyArg_ParseTuple() to exhibit 3.x behaviour in 2.x.  Remove when
# no longer needed

setup(
	name = "pylal",
	version = "0.7.2",
	author = "Kipp Cannon and Nickolas Fotopoulos",
	author_email = "lal-discuss@ligo.org",
	description = "Python LIGO Algorithm Library",
	url = "http://www.lsc-group.phys.uwm.edu/daswg/",
	license = "See file LICENSE",
	packages = [
		"pylal",
	],
	cmdclass = {
		"build_py": pylal_build_py,
		"install": pylal_install,
		"sdist": pylal_sdist
	},
	scripts = [
		os.path.join("bin", "ligolw_cbc_cluster_coincs"),
		os.path.join("bin", "ligolw_cbc_dbinjfind"),
		os.path.join("bin", "ligolw_cbc_hardware_inj_page"),
		os.path.join("bin", "ligolw_cbc_plotcumhist"),
		os.path.join("bin", "ligolw_cbc_plotfm"),
		os.path.join("bin", "ligolw_cbc_plotifar"),
		os.path.join("bin", "ligolw_cbc_plotslides"),
		os.path.join("bin", "ligolw_cbc_printlc"),
		os.path.join("bin", "ligolw_cbc_printmissed"),
		os.path.join("bin", "ligolw_cbc_printsims"),
		os.path.join("bin", "ligolw_cbc_sstinca"),
		os.path.join("bin", "pylal_cbc_minifollowups"),
		os.path.join("bin", "pylal_cbc_plotinspiral"),
		os.path.join("bin", "pylal_cbc_plotinspiralrange"),
		os.path.join("bin", "pylal_cbc_plotnumtemplates"),
		os.path.join("bin", "pylal_cbc_sink"),
		os.path.join("bin", "pylal_cbc_svim")
		],
	data_files = [ ("etc", [
		os.path.join("etc", "pylal-user-env.sh"),
		os.path.join("etc", "pylal-user-env.csh"),
		] ) ]
)
