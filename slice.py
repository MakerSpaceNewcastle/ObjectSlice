#!/usr/bin/env python

import argparse
import multiprocessing
import string
import subprocess
import logging
import os

#==============================================================================

LOG = logging.getLogger(__name__)

SLICER_TEMPLATE = string.Template("""
$import_str
projection(cut=true)
{
  translate([0, 0, -LAYER_HEIGHT-0.001])
  {
    difference()
    {
      union()
      {
        $object_str
      }
      union()
      {
        $key_str
      }
    }
  }
}
""")

#==============================================================================

def execute_slice(args):
    """
    Create new slicing thread.

    @param args Arguments:
        scad_file .scad file used to create slice
        height Height at which to take slice
        output_file DXF file to save to
        openscad OpenSCAD executable
    """

    scad_file, height, output_file, openscad = args
    height_param = "-DLAYER_HEIGHT={0}".format(height)

    try:
        LOG.info("Starting slice at height {0}".format(height))
        subprocess.check_call([openscad,
                               height_param,
                               "-o", output_file,
                               scad_file])
        LOG.info("Completed slice at height {0}".format(height))

    except subprocess.CalledProcessError as cpe:
        LOG.error(str(cpe))

#==============================================================================

class SlicingOperation(object):
    """
    Configuration and runner for a slicing operation.
    """

    def __init__(self, out_format, openscad='openscad', processes=4):
        """
        Create new slicing configuration.

        Output format must include both $height in the file name and end in
        .dxf

        @param out_format Output directory and file format
        @param openscad Executable for OpenSCAD (default: openscad)
        @param processes Number of processes (default: 4)
        """

        self.scad_includes = []
        self.scad_object_modules = []
        self.scad_key_modules = []
        self.keep_scad_file = False
        self.scad_filename = 'object_slice.scad'

        self._out_format = out_format
        self._openscad_command = openscad
        self._processes = processes

        self._scad_include_str = 'include <{0}>;'
        self._slices = []


    def set_slices(self, start=0, end=1, step=None, num=None):
        """
        Sets the slicing.

        Set either step or num, not both.

        @param start Height (in mm) of first slice
        @param end Height (in mm) of end slice
        @param step Step (in mm) between slices
        @param num Number of slices (not guaranteed)
        """

        if step is None:
            s = (end - start) / num
            self._slices = range(start, end + 1, s)
        elif num is None:
            self._slices = range(start, end + 1, step)
        else:
            raise RuntimeError()

        LOG.info('Num slices: %d', len(self._slices))
        LOG.info('Slices: %s', self._slices)


    def slice(self):
        """
        Executes the slicing.
        """

        self._make_output_dir();
        self._make_slice_file();

        out_format = string.Template(self._out_format)
        jobs = [(self.scad_filename, h, out_format.substitute(height=h), self._openscad_command) for h in self._slices]

        pool = multiprocessing.Pool(processes=self._processes)
        pool.map(execute_slice, jobs)

        if not self.keep_scad_file:
            LOG.info('Removing .scad file: %s', self.scad_filename)
            os.remove(self.scad_filename)


    def _make_output_dir(self):
        """
        Creates the output directory if it does not already exist.
        """
        out_dir = os.path.dirname(self._out_format)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        LOG.info('Created output directory: %s', out_dir)


    def _make_slice_file(self):
        """
        Generates the .scad file used to slice the object at a given height.
        """
        import_str = '\n'.join([self._scad_include_str.format(i) for i in self.scad_includes])
        object_str = '\n'.join([m + ';' for m in self.scad_object_modules])
        key_str = '\n'.join([m + ';' for m in self.scad_key_modules])

        contents = SLICER_TEMPLATE.substitute(import_str=import_str,
                                              object_str=object_str,
                                              key_str=key_str,
                                              openscad=self._openscad_command)
        LOG.debug('.scad file contents: %s', contents)

        with open(self.scad_filename, 'w') as f:
            f.write(contents)
        LOG.info('Created .scad file: %s', self.scad_filename)

#==============================================================================

def parse_cli():
    """
    Parses the command line.

    @return Namespace of parsed options
    """

    parser = argparse.ArgumentParser(description='Slice 3D objects into many 2D projections')

    parser.add_argument(
        '-om', '--object-module',
        action='append',
        type=str,
        help='An SCAD module that makes up the object being sliced'
    )

    parser.add_argument(
        '-km', '--key-module',
        action='append',
        type=str,
        help='An SCAD module that makes up the keying of the sliced object'
    )

    parser.add_argument(
        '-i', '--include',
        action='append',
        type=str,
        help='An include that is inserted into the SCAD file'
    )

    parser.add_argument(
        '-st', '--start',
        action='store',
        type=int,
        default=0.0,
        help='Minimum object height to slice from'
    )

    parser.add_argument(
        '-ed', '--end',
        action='store',
        type=int,
        default=100.0,
        help='Maximum object height to slice to'
    )

    parser.add_argument(
        '-s', '--step',
        action='store',
        type=int,
        help='Seperation between slices'
    )

    parser.add_argument(
        '-n', '--number',
        action='store',
        type=int,
        help='Number of slices to make'
    )

    parser.add_argument(
        '-o', '--output',
        action='store',
        type=str,
        default='./out/slice_$height.dxf',
        help='Output directory and format, must contain "$height" and end in ".dxf"'
    )

    parser.add_argument(
        '--scad-filename',
        action='store',
        type=str,
        default='object_slice.scad',
        help='FIlename to save OpenSCAD file that slices a single layer as'
    )

    parser.add_argument(
        '-k', '--keep-scad-file',
        action='store_true',
        default=False,
        help='Keep the OpenSCAD file that slices a single layer'
    )

    parser.add_argument(
        '--openscad-command',
        action='store',
        type=str,
        default='openscad',
        help='Command used to execute OpenSCAD'
    )

    parser.add_argument(
        '-j', '--jobs',
        action='store',
        type=int,
        default=4,
        help='Number oj jobs (processes)'
    )

    parser.add_argument(
        '--log-level',
        action='store',
        type=str,
        default='INFO',
        help='Logging level [DEBUG,INFO,WARNING,ERROR,CRITICAL]'
    )

    props = parser.parse_args()
    return props

#==============================================================================

def run_from_cl(props):
    """
    Configures a SlicingOperation from parsed command line options and executes
    it.

    @param props Parsed options
    """

    # Setup logging
    log_level = getattr(logging, props.log_level.upper(), None)
    if not isinstance(log_level, int):
        log_level = logging.INFO
    logging.basicConfig(level=log_level)
    logging.getLogger(__name__).info('Hello, world!')

    if props.object_module is None:
        sys.out.write('Need at least one object module!\n')
        props.print_help()
        sys.exit(1)

    # Setup slicing
    sc = SlicingOperation(props.output, props.openscad_command, props.jobs)

    sc.scad_object_modules.extend(props.object_module)
    sc.scad_key_modules.extend(props.key_module if props.key_module is not None else [])
    sc.scad_includes.extend(props.include if props.include is not None else [])

    sc.keep_scad_file = props.keep_scad_file
    sc.scad_filename = props.scad_filename

    if props.step:
        sc.set_slices(start=props.start, end=props.end, step=props.step)
    elif props.number:
        sc.set_slices(start=props.start, end=props.end, num=props.number)

    sc.slice()

#==============================================================================

if __name__ == '__main__':
    props = parse_cli()
    run_from_cl(props)
