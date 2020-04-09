"""Tests for TOX modernizer """
import os
import re
from configparser import NoSectionError, ConfigParser
from unittest import TestCase
import shutil
import uuid
from django3_codemods.config_tools.tox_modernizer import ConfigReader


class TestToxModernizer(TestCase):
    def setUp(self):
        current_directory = os.path.dirname(__file__)
        self.file_path = os.path.join(current_directory, str(uuid.uuid4()) + ".ini")
        local_file = os.path.join(current_directory, "sample_tox_config.ini")
        shutil.copy2(local_file, self.file_path)

    def _get_parser(self):
        modernizer = ConfigReader(file_path=self.file_path).get_modernizer()
        modernizer.modernize()
        parser = ConfigParser()
        parser.read(self.file_path)
        return parser

    def test_raises_error_no_empty_config(self):
        tox_config = {}
        self.assertRaises(NoSectionError, ConfigReader(config_dict=tox_config).get_modernizer)

    def test_raises_error_bad_config(self):
        tox_config = {'section1': {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'},
                      'section2': {'keyA': 'valueA', 'keyB': 'valueB', 'keyC': 'valueC'},
                      'section3': {'foo': 'x', 'bar': 'y', 'baz': 'z'}}

        self.assertRaises(NoSectionError, ConfigReader(tox_config).get_modernizer)

    def test_replaces_python_interpreters(self):
        parser = self._get_parser()
        env_list = parser['tox']['envlist']

        self.assertNotRegex("py{27}", env_list)
        self.assertNotIn("py{27,35}", env_list)
        self.assertNotIn("py{27,35,36}", env_list)
        self.assertNotIn("py{27,35,36,37}", env_list)
        self.assertIn("py{38}", env_list)

    def test_replaces_django_runners(self):
        parser = self._get_parser()
        env_list = parser['tox']['envlist']

        self.assertNotIn("django{111}", env_list)
        self.assertNotIn("django{111,20}", env_list)
        self.assertNotIn("django{111,20,21}", env_list)
        self.assertIn("django{22}", env_list)

    def test_django_dependency_replaced(self):
        parser = self._get_parser()
        dependencies = parser['testenv']['deps']

        self.assertNotIn("django111:", dependencies)
        self.assertNotIn("django20:", dependencies)
        self.assertNotIn("django21:", dependencies)
        self.assertIn("django22:", dependencies)

    def test_adds_django_dependency(self):
        parser = ConfigParser()
        parser.read(self.file_path)

        dependencies = parser['testenv']['deps']
        dependencies = re.sub("django22.*\n", '', dependencies)
        parser['testenv']['deps'] = dependencies

        with open(self.file_path, 'w') as configfile:
            parser.write(configfile)

        parser = self._get_parser()
        dependencies = parser['testenv']['deps']

        self.assertNotIn("django111:", dependencies)
        self.assertNotIn("django20:", dependencies)
        self.assertNotIn("django21:", dependencies)
        self.assertIn("django22:", dependencies)

    def tearDown(self):
        os.remove(self.file_path)







