import sys
import re
from configparser import ConfigParser, NoSectionError

TOX_SECTION = "tox"
ENV_SECTION = "envlist"
TEST_ENV_SECTION = "testenv"
TEST_ENV_DEPS = "deps"
PY_38 = "py{38}"
DJANGO_22 = "django{22}"

DJANGO_22_DEPENDENCY = " django22: Django>=2.2,<2.3\n"

SECTIONS = [TOX_SECTION, TEST_ENV_SECTION]


class ConfigReader:
    def __init__(self, file_path=None, config_dict=None):
        self.config_dict = config_dict
        self.file_path = file_path

    def get_modernizer(self):
        config_parser = ConfigParser()
        if self.config_dict is not None:
            config_parser.read_dict(self.config_dict)
        else:
            config_parser.read(self.file_path)
        return ToxModernizer(config_parser, self.file_path)


class ToxModernizer:
    def __init__(self, config_parser, file_path):
        self.file_path = file_path
        self.config_parser = config_parser
        self._validate_tox_config_sections()

    def _validate_tox_config_sections(self):
        if not self.config_parser.sections():
            raise NoSectionError("Bad Config. No sections found.")

        if all(section not in SECTIONS for section in self.config_parser.sections()):
            raise NoSectionError("File doesn't contain required sections")

    def _update_env_list(self):
        tox_section = self.config_parser[TOX_SECTION]
        env_list = tox_section[ENV_SECTION]
        env_list = re.sub("py{.*?}", PY_38, env_list)
        env_list = re.sub("django{.*?}", DJANGO_22, env_list)
        self.config_parser[TOX_SECTION][ENV_SECTION] = env_list

    def _replace_django_versions(self):
        test_environment = self.config_parser[TEST_ENV_SECTION]
        dependencies = test_environment[TEST_ENV_DEPS]
        dependencies = re.sub("django111.*\n", '', dependencies)
        dependencies = re.sub("django20.*\n", '', dependencies)

        has_django22 = re.search("django22.*\n", dependencies) is not None
        substitute = '' if has_django22 else DJANGO_22_DEPENDENCY

        dependencies = re.sub("django21.*\n", substitute, dependencies)
        self.config_parser[TEST_ENV_SECTION][TEST_ENV_DEPS] = dependencies

    def _update_config_file(self):
        with open(self.file_path, 'w') as configfile:
            self.config_parser.write(configfile)

    def modernize(self):
        self._update_env_list()
        self._replace_django_versions()
        self._update_config_file()


if __name__ == '__main__':
    modernizer = ConfigReader(file_path=sys.argv[1]).get_modernizer()
    modernizer.modernize()
