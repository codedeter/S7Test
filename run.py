
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple startup script
"""

print('=' * 50)
print('Starting server...')
print('=' * 50)

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print('Importing modules...')

from src.server import main

print('Calling main()...')
if __name__ == '__main__':
    main()

