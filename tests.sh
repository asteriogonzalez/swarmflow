#!/bin/bash
export PYTHONPATH=.:$PYTHONPATH
py.test -s tests/test_agent.py

