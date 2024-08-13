{ pkgs }: {
  deps = [
    pkgs.gitFull
    pkgs.nano
    pkgs.utillinux
    pkgs.libyaml
    pkgs.playwright-driver
    pkgs.gitFull
    pkgs.playwright-driver.browsers
    pkgs.playwright
  ];
  env = {
    PLAYWRIGHT_BROWSERS_PATH = "${pkgs.playwright-driver.browsers}";
    PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS = true;
  };
}