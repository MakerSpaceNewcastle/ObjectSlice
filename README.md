Object Slice
============

Tool for slicing 3D objects in OpenSCAD into several 2D objects output as DXFs.

Usage
-----

Help: `$ slice.py -h`

Slice a cube: `$ ./slice.py -om "cube([10, 20, 100])" -st 0 -ed 100 -n 20`

Slice an STL: `$ ./slice.py -om "import(\"penguin.stl\", convexity=3)" -st 0 -ed 20 -n 2`

Slice an STL with keying/assembly holes: `$ ./slice.py -om "import(\"penguin.stl\", convexity=3)" -km "cylinder(r=1.5, h=100)" -st 0 -ed 20 -n 2`
