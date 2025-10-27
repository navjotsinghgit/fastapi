#!/bin/bash

cd."$(dirname."$0")"
source.env/bin/activate
uvicorn main:app --reload --host=0.0.0.0 --workers=10