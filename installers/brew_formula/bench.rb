# Documentation: https://github.com/Homebrew/homebrew/blob/master/share/doc/homebrew/Formula-Cookbook.md
#                http://www.rubydoc.info/github/Homebrew/homebrew/master/Formula
# PLEASE REMOVE ALL GENERATED COMMENTS BEFORE SUBMITTING YOUR PULL REQUEST!

class Bench < Formula
  desc "Metadata driven, full-stack web framework"
  homepage "https://github.com/frappe/bench/blob/master/README.md"
  url "https://github.com/nginn/bench/raw/master/installers/rpm_package_build/bench-0.92.tar.gz"
  sha256 ""

  resource "click" do
  url "https://pypi.python.org/packages/source/c/click/click-6.2.tar.gz"
  sha256 "fba0ff70f5ebb4cebbf64c40a8fbc222fb7cf825237241e548354dabe3da6a82"
  end

  resource "jinja2" do
  url "https://pypi.python.org/packages/source/J/Jinja2/Jinja2-2.8.tar.gz"
  sha256 "bc1ff2ff88dbfacefde4ddde471d1417d3b304e8df103a7a9437d47269201bf4"
  end

  resource "virtualenv" do
  url "https://pypi.python.org/packages/source/v/virtualenv/virtualenv-13.1.2.tar.gz"
  sha256 "aabc8ef18cddbd8a2a9c7f92bc43e2fea54b1147330d65db920ef3ce9812e3dc"
  end

  resource "requests" do
  url "https://pypi.python.org/packages/source/r/requests/requests-2.9.1.tar.gz"
  sha256 "c577815dd00f1394203fc44eb979724b098f88264a9ef898ee45b8e5e9cf587f"
  end

  resource "honcho" do
  url "https://pypi.python.org/packages/2.7/h/honcho/honcho-0.6.6-py2.py3-none-any.whl"
  sha256 "40dd530712ce14162ce1bf51f6a5cbb1ab2861da62e5db5816539976a9a5408c"
  end

  resource "semantic_version" do
  url "https://pypi.python.org/packages/source/s/semantic_version/semantic_version-2.4.2.tar.gz"
  sha256 "7e8b7fa74a3bc9b6e90b15b83b9bc2377c78eaeae3447516425f475d5d6932d2"
  end

  resource "gitpython" do
  url "https://pypi.python.org/packages/source/G/GitPython/GitPython-0.3.2.RC1.tar.gz"
  sha256 "fd6786684a0d0dd7ebb961da754e3312fafe0c8e88f55ceb09858aa0af6094e0"
  end
  

  # depends_on "cmake" => :build
  #depends_on :x11s
  depends_on :python if MacOS.version <= :snow_leopard
#  depends_on "honcho"

  def install
    ENV.prepend_create_path "PYTHONPATH", libexec/"vendor/lib/python2.7/site-packages"
    %w[click jinja2 virtualenv requests semantic_version gitpython].each do |r|
      resource(r).stage do
        system "python", *Language::Python.setup_install_args(libexec/"vendor")
      end
    end

    ENV.prepend_create_path "PYTHONPATH", libexec/"lib/python2.7/site-packages"
    system "python", *Language::Python.setup_install_args(libexec)

    bin.install Dir[libexec/"bin/*"]
    bin.env_script_all_files(libexec/"bin", :PYTHONPATH => ENV["PYTHONPATH"])
  end

  test do
    # `test do` will create, run in and delete a temporary directory.
    #
    # This test will fail and we won't accept that! It's enough to just replace
    # "false" with the main program this formula installs, but it'd be nice if you
    # were more thorough. Run the test with `brew test bench`. Options passed
    # to `brew install` such as `--HEAD` also need to be provided to `brew test`.
    #
    # The installed folder is not in the path, so use the entire path to any
    # executables being tested: `system "#{bin}/program", "do", "something"`.
    system "false"
  end
end
