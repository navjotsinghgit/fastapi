#!/bin/bash
while true
do
    uvicorn main:app --host=0.0.0.0 --workers=2
done    
