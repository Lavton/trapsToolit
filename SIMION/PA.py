"""
=pod

=head1 NAME

SIMION.PA - Python (not Lua) module for reading/writing/manipulating SIMION
potential arrays.

=head1 DESCRIPTION

This module is for manipulating SIMION potential array (PA/PA?) files
(including creating, loading, modifying, and saving) in the Python
language.  See Appendix F.5 of the SIMION 8.0 manual (or Appendix
p. D-5 of the SIMION 7.0 manual) for the PA file format specification.
[FIX-TODO: what page number in the 8.1 manual?]

This modules is intended to be very robust and has been put through an
extensive test suite.  It is also intended to be simple to use and
very Pythonic.  The module is, however, not as fast as the
corresponding C++ implementation, even though speed has been
considered, so use the C++ implementation if speed is critical.

=head1 SYNOPSIS

  from SIMION.PA import *
 
  #-- reading an existing array
  pa = PA(file = 'buncher.pa#')
  # print header parameters the simple way
  print pa.header_string()
    
  #-- creating an array from scratch
  pa2 = PA(nx = 100, ny = 20, symmetry = 'cylindrical')
  
  z = 0
  for x in range(0, pa.nx()):
    ...    for y in range(0, pa.ny()):
    ...        inside = (x + y < 10)
    ...        if inside:
    ...            pa.point(x, y, z, 1, 5.0)  # electrode, 5V
  pa2.save('cone.pa#')

  #-- creating a magnetic field from scratch
  pa3 = PA(nx = 50, ny = 50, field_type = 'magnetic')
  z = 0
  for x in range(0, pa.nx()):
      for y in range(0, pa.ny()):
          ex = x
          ey = y**2
          ez = 0
          pa3.field(x, y, z, ex, ey, ez)
  pa3.save('mag1.pa')

=head1 INTERFACE

=cut
"""

#FIX:enable_points

import struct
import re
from math import *

class PAError(Exception):
    """
Exception class for exceptions raised by PA.
    """
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# Read nbytes length bytes from file.  Raises IOError on failure to read nbytes.
def _read_bytes(file, nbytes):
    s = file.read(nbytes)
    if len(s) != nbytes: raise IOError("Bytes missing from file.")
    return s


class PA:
    """
=head2 Class: PA

This is a Python class for reading/writing/modifying SIMION potential arrays.

=cut
    """

    # Group: Construction and Serialization    

    #FIX params
    def __init__(
        self,
        mode            = None,
        symmetry        = None,
        max_voltage     = None,
        nx              = None,
        ny              = None,
        nz              = None,
        mirror          = None,
        mirror_x        = None,
        mirror_y        = None,
        mirror_z        = None,
        field_type      = None,
        ng              = None,
        dx_mm           = None,
        dy_mm           = None,
        dz_mm           = None,
        fast_adjustable = None,
        enable_points   = None,
        file            = None
    ):
        """
=head3 Constructor: PA

Creates a new array.

To load an array from a file, do

  pa = PA(file = 'buncher.pa#')

To create an array from scratch (with all points initially set to 0V
non-electrodes) do

  pa = PA(
  mode = -1,               # mode (always -1)
  symmetry = 'planar',     # symmetry type: 'planar' or 'cylindrical'
  max_voltage = 100000,    # this affects the interpretation
                           #   of point values
  nx = 100,                # x dimension in grid units
  ny = 100,                # y dimension in grid units
  nz = 1,                  # z dimension in grid units
  mirror = '',             # mirroring (subset of "xyz")
  field_type =             # field type: 'electrostatic' or 'magnetic'
      'electrostatic',     #
  ng = 100,                # ng scaling factor for magnetic arrays.
  # The following three fields are only supported in SIMION 8.1
  dx_mm = 1,               # grid unit size (mm) in X direction
  dy_mm = 1,               # grid unit size (mm) in Y direction
  dz_mm = 1,               # grid unit size (mm) in Z direction
  fast_adjustable = 0,     # Boolean indicating whether is fast-adj.
  enable_points = 1        # Enable data points.
  )

See the section of the SIMION manual discussed above
for details on these parameters.
The parameters given above are default values, and any/all can be
omitted:

  pa = PA();
  pa = PA(nx = 100, ny = 20, field_type = 'magnetic')

=cut
        """

        self._mode            = None
        self._symmetry        = None
        self._max_voltage     = None
        self._nx              = None
        self._ny              = None
        self._nz              = None
        self._mirror          = None
        self._mirror_x        = None
        self._mirror_y        = None
        self._mirror_z        = None
        self._field_type      = None
        self._ng              = None
        self._dx_mm           = None
        self._dy_mm           = None
        self._dz_mm           = None
        self._enable_points   = None
        self._fast_adjustable = None
        self._file            = None
        self._error           = None
        self._pasharp         = None

        if file == None: # defaults
            if mode == None:            mode = -1
            #FIX:use constants to prevent typos?
            if symmetry == None:        symmetry = 'planar'
            if max_voltage == None:     max_voltage = 100000.0
            if nx == None:              nx = 3
            if ny == None:              ny = 3
            if nz == None:              nz = 1
            # mirror
            # mirror_x
            # mirror_y
            # mirror_z
            if field_type == None:      field_type = 'electrostatic'
            if ng == None:              ng = 100
            if dx_mm == None:           dx_mm = 1
            if dy_mm == None:           dy_mm = 1
            if dz_mm == None:           dz_mm = 1
            if fast_adjustable == None: fast_adjustable = 0
            if enable_points == None:   enable_points = 1

            if mirror == None and mirror_x == None and mirror_y == None and mirror_z == None:
                mirror_x = 0
                mirror_y = (symmetry == 'cylindrical')
                mirror_z = 0

        self.set(
            mode            = mode,
            symmetry        = symmetry,
            max_voltage     = max_voltage,
            nx              = nx,
            ny              = ny,
            nz              = nz,
            mirror          = mirror,
            mirror_x        = mirror_x,
            mirror_y        = mirror_y,
            mirror_z        = mirror_z,
            field_type      = field_type,
            ng              = ng,
            dx_mm           = dx_mm,
            dy_mm           = dy_mm,
            dz_mm           = dz_mm,
            fast_adjustable = fast_adjustable,
            enable_points   = enable_points,
            file            = file
        )

    def header_string(self):
        """
=head3 header_string

  s = pa.header_string()

Returns a string containing PATXT-formatted header for the
current array.

For example, for SIMION's QUAD.PA# file, the result is as
such:
 
  begin_header
      mode -1
      symmetry planar
      max_voltage 20000
      nx 77
      ny 39
      nz 1
      mirror_x 0
      mirror_y 1
      mirror_z 0
      field_type electrostatic
      ng 100
      fast_adjustable 1
  end_header

May also contain these fields:

  dx_mm 1.0
  dy_mm 1.0
  dz_mm 1.0

This method is also very useful for debugging to quickly display the
information on a given potential array.

Returns: string containing header information as text.

=cut
        """
        text = \
"begin_header\n"       + \
"    mode "            + str(self.mode()) + "\n" + \
"    symmetry "        + self.symmetry() + "\n" + \
"    max_voltage "     + str(self.max_voltage()) + "\n" + \
"    nx "              + str(self.nx()) + "\n" + \
"    ny "              + str(self.ny()) + "\n" + \
"    nz "              + str(self.nz()) + "\n" + \
"    mirror_x "        + (self.mirror_x() and "1" or "0") + "\n" + \
"    mirror_y "        + (self.mirror_y() and "1" or "0") + "\n" + \
"    mirror_z "        + (self.mirror_z() and "1" or "0") + "\n" + \
"    field_type "      + self.field_type() + "\n" + \
"    ng "              + str(self.ng()) + "\n"

        if self.mode() <= -2:
            text += \
"    dx_mm "     + str(self.dx_mm()) + "\n" + \
"    dy_mm "     + str(self.dy_mm()) + "\n" + \
"    dz_mm "     + str(self.dz_mm()) + "\n"

        text += \
"    fast_adjustable " + (self.fast_adjustable() and "1" or "0") + "\n" + \
"end_header\n"
        return text

        
    def load(self, path):
        """
=head3 load

  pa.load(path)

Loads a potential array from a file.

Note, arrays can also be loaded in the new method.
Example:

  pa.load('myfile.pa#')

=over

=item C<path> - string containing relative or absolute path to file.

=back

On error, raises PAError.

=cut
        """
        try:
            f = None
            f = open(path, 'rb')
            (mode,) = struct.unpack("i", _read_bytes(f, 4))
            if mode != -1 and mode != -2:
                raise PAError("invalid mode (%(mode)d)" % {'mode': mode})
            (symmetry, max_voltage, nx, ny, nz, raw_mirror) \
                = struct.unpack("=idiiii", _read_bytes(f, 4 + 8 + 4*4))
            if mode <= -2:
                (dx_mm, dy_mm, dz_mm) \
                = struct.unpack("ddd", _read_bytes(f, 8*3))
            else:
                (dx_mm, dy_mm, dz_mm) = (1,1,1)

            self._mode = mode
            self._symmetry = symmetry and "planar" or "cylindrical"
            self._max_voltage = max_voltage
            self._nx = nx
            self._ny = ny
            self._nz = nz
            self._mirror_x = raw_mirror & 1
            self._mirror_y = (raw_mirror >> 1) & 1
            self._mirror_z = (raw_mirror >> 2) & 1
            self._field_type = ((raw_mirror >> 3) & 1) and "magnetic" or "electrostatic"
            self._ng = (raw_mirror >> 4) & ((1 << 17)-1)
            self._dx_mm = dx_mm
            self._dy_mm = dy_mm
            self._dz_mm = dz_mm
            self._fast_adjustable = re.search('#$', path) != None
            # self._enable_points = 

            fx = "d" * self._nx
            num_points = self._nx * self._ny * self._nz
            self._points = [0] * num_points # allocate
            for n in range(0, num_points, self._nx):
                buf = f.read(self._nx * 8)
                self._points[n:n+self._nx] = list(struct.unpack(fx, buf))
            f.close()                
        except PAError as e:
            if f: f.close()
            raise PAError("Failed reading file \"" + path + "\": " + str(e))
        except IOError as e:
            if f: f.close()
            raise PAError("Failed reading file \"" + path + "\": " + str(e))
 

    #FIX:what if fails?
    def save(self, path):
        """
=head3 save

  pa.save(path)

Saves potential array to file.

  pa.save('myfile.pa#')

=over

=item C<path> - relative or absolute path to file.

=back

On failure, raises PAError.

=cut
        """

        # normalize
        self._mirror_x &= 0x1;
        self._mirror_y &= 0x1;
        self._mirror_z &= 0x1;

        try:
            f = open(path, 'wb')
                                            
            symmetry = (self._symmetry == "planar") and 1 or 0

            raw_mirror = 0
            if self._mirror_x: raw_mirror |= 1
            if self._mirror_y: raw_mirror |= 2
            if self._mirror_z: raw_mirror |= 4
            if self._field_type == "magnetic": raw_mirror |= 8
            if self._ng >= 1 and self._ng <= 90000 and self._ng == floor(self._ng):
                raw_mirror |= (self._ng << 4)
            header_str = struct.pack("iidiiii", self.mode(), symmetry, self._max_voltage, \
                self._nx, self._ny, self._nz, raw_mirror)
            if self.mode() <= -2:
                header_str += struct.pack("ddd", \
                    self._dx_mm, self._dy_mm, self._dz_mm)

            f.write(header_str)
                                            
            fx = "d" * self._nx
            num_points = len(self._points)
            for n in range(0, num_points, self._nx):
                buf = struct.pack(fx, *self._points[n:n+self._nx])
                f.write(buf)

            # record stats in PA0 file.
            if self._pasharp != None:
                assert self._pasharp.nx() == self.nx() and self._pasharp.ny() == self.ny() \
                          and self._pasharp.nz() == self.nz(), \
                          "PA# dimensions does not match PA0 dimensions"

                first_idx = [-1] * 31

                for n in range(0, num_points):
                    fval = self._pasharp._points[n]
                    if fval >= 2 * self._pasharp.max_voltage():  # electrode
                        fval -= 2 * self._pasharp.max_voltage()
    
                        ival = int(fval)
                        if ival == fval and ival >= 1 and ival <= 30: # fast adjustable
                            if first_idx[ival] == -1:
                                # print ival, " ", n, "\n"
                                first_idx[ival] = n;
                        elif first_idx[0] == -1: # fast scalable
                            first_idx[0] = n

    
                num_electrodes = (first_idx[0] != -1) and 1 or 0;
                for n in range(1, 31):
                    if first_idx[n] != -1:
                        num_electrodes = num_electrodes+1

                f.write(struct.pack("i", num_electrodes))
                f.write(struct.pack("d", 10000.0))

                for n in range(0, 31):
                    f.write(struct.pack("i", first_idx[n]))

                f.write(struct.pack("i", -1))

            f.close()
        except IOError as e:
            if f: f.close()
            raise PAError("Failed writing file \"" + path + "\": " + str(e))

    # Group: Getters and Setters
        
#FIX:enable_points?
    def fast_adjustable(self, fast_adjustable=None):
        """
=head3 fast_adjustable

  fast_adjustable = pa.fast_adjustable()
  pa.fast_adjustable(fast_adjustable)

Gets or sets whether the array is fast adjustable.

  pa.fast_adjustable(1)
  print pa.fast_adjustable()

=over

=item C<fast_adjustable> - Boolean indicating whether array is fast adjustable
(if setting)

=back

Returns: fast_adjustable (if getting)

=cut
        """
        if fast_adjustable == None: return self._fast_adjustable
        self._fast_adjustable = not not fast_adjustable

    def field_type(self, field_type=None):
        """
=head3 field_type

  field_type = pa.field_type()
  pa.field_type(field_type)

Gets or sets the field type as a string.

This is either "electrostatic" or "magnetic".

  pa.field_type('magnetic')
  print pa.field_type()

=over

=item C<field_type> - string containing field type identifier (if setting).

=back

Returns: field_type (if getting)

=cut
        """
        if field_type == None: return self._field_type
        assert self.check_field_type(field_type), self.error()
        self._field_type = field_type

    def mode(self, mode=None):
        """
=head3 mode

  mode = pa.mode()
  pa.mode(mode)

Gets or sets the recommended file format (mode) number.  -1: SIMION 7.0/8.0.
-2: SIMION 8.1 anisotropic scaling.  The value returned may be more negative
than the value provided if the PA uses capabilities not supported in the given
mode.

  pa.mode(-1)
  print pa.mode()

=over

=item C<mode> - integer containing mode number (if setting).

=back

Returns: mode (if getting).

=cut
        """
        if mode == None:
            if self._mode == -1 and (self._dx_mm != 1 or
                                     self._dy_mm != 1 or
                                     self._dz_mm != 1):
                return -2
            return self._mode
        assert self.check_mode(mode), self.error()
        self._mode = mode
                                            
    def max_voltage(self, max_voltage=None):
        """
=head3 max_voltage

  max_voltage = pa.max_voltage()
  pa.max_voltage(max_voltage)

Gets or sets the max voltage value.

  pa.max_voltage(100000)
  print pa.max_voltage()

=over

=item C<max_voltage> - number containing max voltage value (if setting).

=back

Returns: max_voltage (if getting).

As of 2007-07-11, increasing this updates the array values.
Result is undefined if max_voltage is decreased below
the maximum potential in the array.

=cut
        """
        if max_voltage == None: return self._max_voltage
        assert self.check_max_voltage(max_voltage), self.error()

        num_points = self._nx * self._ny * self._nz

        old_max_voltage = self._max_voltage
        diff = -2 * self._max_voltage + 2 * max_voltage

        self._max_voltage = max_voltage
        for n in range(num_points):
            if self._points[n] > old_max_voltage:
                self._points[n] += diff

    def mirror(self, mirror=None):
        """
=head3 mirror

  mirror = pa.mirror()
  pa.mirror(mirror)

Gets or sets the full mirroring information.

  pa.mirror('yz')
  print pa.mirror()

The above is equivalent to

  pa.set(mirror_y = 1, mirror_z = 1)

=over

=item C<mirror> - string containing a subset of the letters "xyz".  (if setting)

=back

Returns: mirror (if getting)

=cut
        """
        if mirror == None:
            str = ''
            if self._mirror_x: str += 'x'
            if self._mirror_y: str += 'y'
            if self._mirror_z: str += 'z'
            return str
        else:
            # assert self.check_mirror(mirror), self.error()
            m = re.match('^(x?)(y?)(z?)$', mirror)
            assert m != None, 'Mirror string (' + mirror + ') is invalid.'
            self._mirror_x = m.group(1) != ''
            self._mirror_y = m.group(2) != ''
            self._mirror_z = m.group(3) != ''

    def mirror_x(self, mirror_x=None):
        """
=head3 mirror_x

  mirror_x = pa.mirror_x()
  pa.mirror_x(mirror_x)

Gets or sets a Boolean indicating whether the mirroring is enabled in the x
direction.

  pa.mirror_x(1)
  print pa.mirror_x()

=cut
        """
        if mirror_x == None: return self._mirror_x
        self._mirror_x = not not mirror_x

    def mirror_y(self, mirror_y=None):
        """
=head3 mirror_y

  mirror_y = pa.mirror_y()
  pa.mirror_y(mirror_y)

Gets or sets a Boolean indicating whether the mirroring is enabled in the y
direction.

  pa.mirror_y(1)
  print pa.mirror_y()

=cut
        """
        if mirror_y == None: return self._mirror_y
        assert self.check(
            nx = self._nx, ny = self._ny, nz = self._nz,
            symmetry = self._symmetry,
            mirror_x = self._mirror_x,
            mirror_y = mirror_y,
            mirror_z = self._mirror_z
        ), self.error()
        self._mirror_y = not not mirror_y

    def mirror_z(self, mirror_z=None):
        """
=head3 mirror_z

  mirror_z = pa.mirror_z()
  pa.mirror_z(mirror_z)

Gets or sets a Boolean indicating whether the mirroring is enabled in the z
direction.

  pa.mirror_z(1)
  print pa.mirror_z()

=cut
        """
        if mirror_z == None: return self._mirror_z
        assert self.check(
            nx = self._nx, ny = self._ny, nz = self._nz,
            symmetry = self._symmetry,
            mirror_x = self._mirror_x,
            mirror_y = self._mirror_y,
            mirror_z = mirror_z
        ), self.error()
        self._mirror_z = not not mirror_z

    def ng(self, ng=None):
        """
=head3 ng

  ng = pa.ng()
  pa.ng(ng)

Gets or sets the ng magnetic scaling factor.

  pa.ng(100)
  print pa.ng()

=over

=item C<ng> - integer containing the magnetic scalaing factor (if setting).

=back

Returns: ng (if getting)

=cut
        """
        if ng == None: return self._ng
        assert self.check_ng(ng), self.error()
        self._ng = ng

    def num_points(self):
        """
=head3 num_points

  num_points = pa.num_points()

Gets the number of grid points.

This is nx() * ny() * nz().

  pa = PA(nx = 3, ny = 4)
  print pa.num_points()   # prints 12

Returns: integer containing number of grid points.

=cut
        """
        return self._nx * self._ny * self._nz

    def num_voxels(self):
        """
=head3 num_voxels

  num_voxels = pa.num_voxels()

Gets the number of voxels (2D or 3D pixels).

Each voxel is surrounded
by four (2D arrays) or eight (3D arrays) grid points.
For 2D arrays, this is (nx()-1) * (ny()-1).  For 3D arrays, this is
(nx()-1) * (ny()-1) * (nz()-1).

  pa = PA(nx = 3, ny = 4)
  print pa.num_voxels()   # prints 6

Returns: integer containing number of voxels.

=cut
        """
        num = (self._nx - 1) * (self._ny - 1)
        if self._nz != 1: num *= (self._nz - 1)
        return num

    def nx(self, nx=None):
        """
=head3 nx

  nx = pa.nx()
  pa.nx(nx)

Gets or sets the number of grid points in the x direction.
                  
Point data is cleared on resizing.

  pa.nx(100)
  print pa.nx()

=over

=item C<nx> - integer containing x dimension in grid points (if setting).

=back

Returns: nx (if getting).

=cut
        """
        if nx == None: return self._nx
        assert self.check(
            nx = nx, ny = self._ny, nz = self._nz,
            symmetry = self._symmetry,
            mirror_x = self._mirror_x,
            mirror_y = self._mirror_y,
            mirror_z = self._mirror_z
        ), self.error()
        self.size(nx, self._ny, self._nz)

    def ny(self, ny=None):
        """
=head3 ny

  ny = pa.ny()
  pa.ny(ny)

Gets or sets the number of grid points in the y direction.
                  
Point data is cleared on resizing.

  pa.ny(100)
  print pa.ny()

=over

=item C<ny> - integer containing y dimension in grid points (if setting).

=back

Returns: ny (if getting).

=cut
        """
        if ny == None: return self._ny
        assert self.check(
            nx = self._nx, ny = ny, nz = self._nz,
            symmetry = self._symmetry,
            mirror_x = self._mirror_x,
            mirror_y = self._mirror_y,
            mirror_z = self._mirror_z
        ), self.error()
        self.size(self._nx, ny, self._nz)

    def nz(self, nz=None):
        """
=head3 nz

  nz = pa.nz()
  pa.nz(nz)

Gets or sets the number of grid points in the z direction.
                  
Point data is cleared on resizing.

  pa.nz(100)
  print pa.nz()

=over

=item C<nz> - integer containing z dimension in grid points (if setting).

=back

Returns: nz (if getting).

=cut
        """
        if nz == None: return self._nz
        assert self.check(
            nx = self._nx, ny = self._ny, nz = nz,
            symmetry = self._symmetry,
            mirror_x = self._mirror_x,
            mirror_y = self._mirror_y,
            mirror_z = self._mirror_z
        ), self.error()
        self.size(self._nx, self._ny, nz)


    def pasharp(self, pasharp=None):
        """
=head3 pasharp

  pasharp = pa.pasharp()
  pa.pasharp(pasharp)

Gets or sets the PA# associated with this PA0 (if any).  None if
none.  This is only intended for PA0 arrays.  The PA# information is
needed to properly save a PA0 file.

  pasharp = PA(file = "test.pa#")
  pa0 = PA()
  # ... add code to create pa0 array here.
  pa0.pasharp(pasharp)
  pa0.save("test.pa0")

=over

=item pasharp - PA# potential array object

=back

Returns: PA# potential array object

=cut
        """

        if pasharp == None: return self._pasharp
        self._pasharp = pasharp

    def set(
        self,
        mode=None,
        symmetry=None,
        max_voltage=None,
        nx=None, ny=None, nz=None,
        mirror=None,
        mirror_x=None,
        mirror_y=None,
        mirror_z=None,
        field_type=None,
        ng=None,
        dx_mm=None,
        dy_mm=None,
        dz_mm=None,
        fast_adjustable=None,
        enable_points=None,
        file=None
    ):
        """
=head3 set

  pa.set(...)

Sets multiple attributes at once.

This can take the same set of parameters
as the new() method.  This method is useful when the attributes are
interdependent.  Asserts on error.

  pa.set(nz = 1, symmetry = 'cylindrical')

See the individual setter methods for details on each parameter.

=cut
        """

        if file != None:
            assert mode == None and symmetry == None and max_voltage == None and \
               nx == None and ny == None and nz == None and mirror == None and \
               mirror_x == None and mirror_y == None and mirror_z == None and \
               field_type == None and ng == None and fast_adjustable == None and \
               enable_points == None and dx_mm == None and \
               dy_mm == None and dz_mm == None, \
                "Named parameter 'file' cannot coexist with other named parameters."
            self.load(file);
        else:
            # aliases
            if mirror != None:
                assert mirror_x == None, "mirror and mirror_x named parameters cannot coexist."
                assert mirror_y == None, "mirror and mirror_y named parameters cannot coexist."
                assert mirror_z == None, "mirror and mirror_z named parameters cannot coexist."

                (mirror_x, mirror_y, mirror_z) = self._parse_mirror(mirror)

            # defaults
            if symmetry == 'cylindrical' and mirror_y == None:
                mirror_y = 1


            # checks
            assert mode == None or        self.check_mode(mode), \
                                          self.error()
            assert max_voltage == None or self.check_max_voltage(max_voltage), \
                                          self.error()
            assert field_type == None or  self.check_field_type(field_type), \
                                          self.error()
            assert ng == None or          self.check_ng(ng), \
                                          self.error()
            assert symmetry == None or    self.check_symmetry(symmetry), \
                                          self.error()
            assert dx_mm == None or       self.check_dx_mm(dx_mm), \
                                          self.error()
            assert dy_mm == None or       self.check_dy_mm(dy_mm), \
                                          self.error()
            assert dz_mm == None or       self.check_dz_mm(dz_mm), \
                                          self.error()

            if mirror_x != None or mirror_y != None or mirror_z != None:
                if mirror_x == None: mirror_x = self._mirror_x
                if mirror_y == None: mirror_y = self._mirror_y
                if mirror_z == None: mirror_z = self._mirror_z
                mirror_str = ''
                if mirror_x: mirror_str += 'x'
                if mirror_y: mirror_str += 'y'
                if mirror_z: mirror_str += 'z'

                assert self.check_mirror(mirror_str), self.error()

            if nx != None or ny != None or nz != None:
                if nx == None: nx = self._nx
                if ny == None: ny = self._ny
                if nz == None: nz = self._nz
                assert self.check_size(nx, ny, nz), self.error()

            if symmetry == None: symmetry = self._symmetry
            if mirror_x == None: mirror_x = self._mirror_x
            if mirror_y == None: mirror_y = self._mirror_y
            if mirror_z == None: mirror_z = self._mirror_z
            if nx == None: nx = self._nx
            if ny == None: ny = self._ny
            if nz == None: nz = self._nz
            assert self.check(
                nx = nx, ny = ny, nz = nz, symmetry = symmetry,
                mirror_x = mirror_x,
                mirror_y = mirror_y,
                mirror_z = mirror_z
            ), self.error()

            # assert: no throws below this point.

            # set
            if mode != None: self._mode = mode
            if max_voltage != None: self._max_voltage = max_voltage
            if field_type != None: self._field_type = field_type
            if ng != None: self._ng = ng
            if fast_adjustable != None: self._fast_adjustable = not not fast_adjustable
            if enable_points != None: self._enable_points = not not enable_points
            if symmetry != None: self._symmetry = symmetry
            if mirror_x != None: self._mirror_x = mirror_x
            if mirror_y != None: self._mirror_y = mirror_y
            if mirror_z != None: self._mirror_z = mirror_z
            if dx_mm != None: self._dx_mm = dx_mm
            if dy_mm != None: self._dy_mm = dy_mm
            if dz_mm != None: self._dz_mm = dz_mm
    #FIX:not throws?
            if nx != None and (nx != self._nx or ny != self._ny or nz != self._nz):
                self.size(nx, ny, nz)


    def size(self, nx=None, ny=None, nz=None):
        """
=head3 size

  (nx, ny, nz) = pa.size()
  pa.size(nx, ny, nz)

Gets or sets the size for the array in grid points.
                  
Point data is cleared on resizing.

  pa.size(10, 20, 30)
  (nx, ny, nz) = pa.size()

=over

=item C<nx> - integer containing x dimension in grid points (if setting).

=item C<ny> - integer containing y dimension in grid points (if setting).

=item C<nz> - integer containing z dimension in grid points (if setting).

=back

Returns: (nx, ny, nz) tuple (if getting)

=cut
        """
        if nx == None: return (self._nx, self._ny, self._nz)

        if nz == None: nz = 1

        assert self.check(
            nx = nx, ny = ny, nz = nz, symmetry = self._symmetry,
            mirror_x = self._mirror_x,
            mirror_y = self._mirror_y,
            mirror_z = self._mirror_z
        ), self.error()
        self._nx = nx;
        self._ny = ny;
        self._nz = nz;

        self._points = [0] * (nx * ny * nz)

    def symmetry(self, symmetry=None):
        """
=head3 symmetry

  symmetry = pa.symmetry()
  pa.symmetry(symmetry)

Gets or sets the symmetry.

  pa.symmetry('cylindrical')
  print pa.symmetry()

=over

=item C<symmetry> - string containing symmetry identifier (if setting).
This is either 'planar' or 'cylindrical'.

=back

Returns: symmetry (if getting).

=cut
        """
        if symmetry == None: return self._symmetry
        assert self.check(
            nx = self._nx, ny = self._ny, nz = self._nz,
            symmetry = symmetry,
            mirror_x = self._mirror_x,
            mirror_y = self._mirror_y,
            mirror_z = self._mirror_z
        ), self.error()
        self._symmetry = symmetry

    def dx_mm(self, value=None):
        """
=head3 dx_mm

  dx_mm = self.dx_mm()
  pa.dx_mm(dx_mm)

Gets or sets the grid unit size (mm) in the x direction.  Requires SIMION 8.1.

  pa.dx_mm(1)
  print pa.dx_mm()

=over

=item C<dx_mm> - double representing mm (if setting).

=back

=cut
        """
        if value == None: return self._dx_mm
        assert self.check_dx_mm(value), self.error()
        self._dx_mm = value

    def dy_mm(self, value=None):
        """
=head3 dy_mm

  dy_mm = self.dy_mm()
  pa.dy_mm(dy_mm)

Gets or sets the grid unit size (mm) in the y direction.  Requires SIMION 8.1.

  pa.dy_mm(1)
  print pa.dy_mm()

=over

=item C<dy_mm> - double representing mm (if setting).

=back

=cut
        """
        if value == None: return self._dy_mm
        assert self.check_dy_mm(value), self.error()
        self._dy_mm = value

    def dz_mm(self, value=None):
        """
=head3 dz_mm

  dz_mm = self.dz_mm()
  pa.dz_mm(dz_mm)

Gets or sets the grid unit size (mm) in the z direction.  Requires SIMION 8.1.

  pa.dz_mm(1)
  print pa.dz_mm()

=over

=item C<dz_mm> - double representing mm (if setting).

=back

=cut
        """
        if value == None: return self._dz_mm
        assert self.check_dz_mm(value), self.error()
        self._dz_mm = value

    # Group: Boundary and Coordinates

    def inside(self, x, y, z):
        """
=head3 inside

  is_inside = pa.inside(x, y, z)

Returns a Boolean indicating whether the given integer point
is located within the array.

  if pa.inside(10, 20, 30): print 'inside'

=over

=item C<x> - integer containing x position in grid points (zero indexed).

=item C<y> - integer containing y position in grid points (zero indexed).

=item C<z> - integer containing z position in grid points (zero indexed).

=back

Returns: Boolean indicating whether point is inside.

=cut
        """
        yes = (x >= 0 and x < self._nx and
               y >= 0 and y < self._ny and
               z >= 0 and z < self._nz)
        return yes

    def inside_real(self, x, y, z):
        """
=head3 inside_real

  is_inside = pa.inside_real(x, y, z)

Returns a Boolean indicating whether the given real (i.e. floating-point)
point is located within the array, taking symmetry and mirroring into
account.  Note that inside($x, $y, $z) implies inside_real($x, $y, $z),
although the converse is not necessarily true.

  if pa.inside(-10.1, 20.2, 30.3): print 'inside'

=over

=item C<x> - real number containing x position in grid points.

=item C<y> - real number containing y position in grid points.

=item C<z> - real number containing z position in grid points.

=back

Returns: Boolean indicating whether point is inside.

=cut
        """
        yes = 0
        if self._symmetry == 'planar':
            if x >= 0.0:
                yes = (x <= self._nx-1)
            elif self.mirror_x():
                yes = (-x <= self._nx-1)
            else:
                yes = 0

            if yes:                  
                if y >= 0.0:
                    yes = (y <= self._ny-1)
                elif self.mirror_y():
                    yes = (-y <= self._ny-1)
                else:
                    yes = 0
                if yes and self._nz != 1: # infinite extent
                    if z >= 0.0:
                        yes = (z <= self._nz-1)
                    elif self.mirror_z():
                        yes = (-z <= self._nz-1)
                    else:
                        yes = 0
        elif self._symmetry == 'cylindrical':
            r = sqrt(y*y + z*z)
            yes = self._inside_cylindrical_real(x, r)
        else: assert 0, "internal error: bad symmetry (" + self._symmetry + ")"
        return yes

    def voxel_inside(self, x, y, z):
        """
=head3 voxel_inside

  is_inside = pa.voxel_inside(x, y, z)

Returns a Boolean indicating whether the given integer voxel is
located within the array.

The voxel is specified by its most negative
grid point corner--for example, (2, 3, 4) represents the voxel
contained in the box [2..3, 3..4, 4..5].  Note that voxel_inside(x,
y, z) implies inside(x, y, z), although the converse is not
necessarily true.

  if pa.voxel_inside(10, 20, 30): print 'inside'

=over

=item C<x> - integer containing x position in grid points.

=item C<y> - integer containing y position in grid points.

=item C<z> - integer containing z position in grid points.

=back

Returns: Boolean indicating whether voxel is inside.

=cut
        """
        yes = x >= 0 and x + 1 < self._nx and \
              y >= 0 and y + 1 < self._ny
        if yes:
            if self._nz == 1:
                yes = z == 0
            else:
                 yes = z >= 0 and z + 1 < self._nz
        return yes


    # Group: Point Setters/Getters:

    def clear_points(self):
        for n in range(0, self.num_points()):
            self._points[n] = 0.0

    #FIX:use xi rather than x to denote integer points
    def electrode(self, x, y, z=0, is_electrode=None):
        """
=head3 electrode

  is_val = pa.electrode(x, y, z)
  pa.electrode(x, y, z, is_val)

Gets or sets the Boolean electrode state at the given
integer point.

  pa.electrode(10, 20, 30, 1)
  print pa.electrode(10, 20, 30)

=over

=item C<x> - integer containing x position in grid points.

=item C<y> - integer containing y position in grid points.

=item C<z> - integer containing z position in grid points.

=item C<is_val> - is electrode, Boolean (if setting)

=back

Returns: Boolean indicating whether point is an electrode (if getting).

=cut
        """
        assert self.inside(x,y,z), self._fail_point(x,y,z)

        pos = (z * self._ny + y) * self._nx + x
        if is_electrode == None:
            return (self._points[pos] > self._max_voltage)
        else:
            if self._points[pos] > self._max_voltage:
                if not is_electrode: self._points[pos] -= 2 * self._max_voltage
            else:
                if is_electrode: self._points[pos] += 2 * self._max_voltage

    def field(self, x, y, z=0, ex=None, ey=None, ez=None):
        """
=head3 field

  (ex, ey, ez) = pa.field(x, y, z)
  pa.field(x, y, z, ez, ey, ez)

Gets or sets the field (potential gradient) vector at the given point.

The setting function internally performs the numerical integration on
the given field vectors to generate the corresponding scalar
potentials that must be stored in the PA file.  Dies on error.

Warning: The setting function
has some special calling requirements.  First, the all points
must initially be zero volt, nonelectrodes.  Second, the field
setting method must be called for all points in the array in
lexographic order (e.g. (0,0,0), (0,0,1), ... (0,0,nx()-1), (0,1,0),
(0,1,1), (0,1,nx()-1), ...).

  # set
  for z in range(0,pa.nz()):
      for y in range(0,pa.ny()):
          for x in range(0,pa.nx()):
              ex = x
              ey = y**2
              ez = 0
              pa.field(x, y, z, ex, ey, ez)
  
  (ex, ey, ez) = pa.field(10, 20, 30)  # get

=cut
        """
        if ex == None: # get
            assert self.inside(x,y,z), self._fail_point(x,y,z)
            return self.field_real(x,y,z)
        else: # set
            self._set_field(x,y,z,ex,ey,ez)

    def field_real(self, x, y, z=0):
        """
=head3 field_real

  (ex, ey, ez) = pa.field_real(x, y, z)

Gets the electrostatic or magnetic field vector (ex, ey, ez)
at the given real point, taking symmetry and mirroring into account.

  # assuming mirror_x
  (ex, ey, ez) = pa.field_real(-10.3, 20.2, 30.7)

=over

=item C<x> - real number containing x position in grid points.

=item C<y> - real number containing y position in grid points.

=item C<z> - real number containing z position in grid points.

=back

Returns: (ex, ey, ez) tuple, where ex, ey, and ez are real numbers
containing the x, y, and z components of the field vector respectively.

=cut
        """

        assert self.inside_real(x,y,z), self._fail_point(x,y,z)

        if self._symmetry == 'cylindrical':
            r = sqrt(y*y + z*z)

            #FIX:Q:is there a better way to handle boundary conditions?
            xm = x - 0.5
            min_x = self.mirror_x() and -(self._nx-1) or 0
            if xm < min_x: xm = min_x

            xp = x + 0.5
            if xp > self._nx-1: xp = self._nx-1

            rm = r - 0.5
            min_r = -(self._ny-1)
            if rm < min_r: rm = min_r # won't occur?

            rp = r + 0.5
            if rp > self._ny-1: rp = self._ny-1

            # FIX:Q:should the sampling be done before or after
            # applying cylindrical symmetry?
            V2 = self.potential_real(xp, r,  0.0)
            V1 = self.potential_real(xm, r,  0.0)
            V4 = self.potential_real(x,  rp, 0.0)
            V3 = self.potential_real(x,  rm, 0.0)

            # print "V1, V2, V3, V4\n"

            Ex = (V1 - V2) / (xp - xm)
            Er = (V3 - V4) / (rp - rm)
            Ey = Er * (r == 0 and 1 or y/r)
            Ez = Er * (r != 0 and z/r or 0.0)
            if self._field_type == 'magnetic':
                Ex *= self._ng
                Ey *= self._ng
                Ez *= self._ng
                Er *= self._ng
            return (Ex, Ey, Ez)
        else: # planar
            #FIX:Q:is there a better way to handle boundary conditions?
            xm = x - 0.5
            min_x = self.mirror_x() and -(self._nx-1) or 0
            if xm < min_x: xm = min_x

            xp = x + 0.5
            if xp > self._nx-1: xp = self._nx-1

            ym = y - 0.5
            min_y = self.mirror_y() and -(self._ny-1) or 0
            if ym < min_y: ym = min_y

            yp = y + 0.5
            if yp > self._ny-1: yp = self._ny-1

            zm = z - 0.5
            min_z = self.mirror_z() and -(self._nz-1) or 0
            if zm < min_z: zm = min_z

            zp = z + 0.5
            if zp > self._nz-1: zp = self._nz-1
            V2 = self.potential_real(xp, y,  z)
            V1 = self.potential_real(xm, y,  z)
            V4 = self.potential_real(x,  yp, z)
            V3 = self.potential_real(x,  ym, z)
            V5 = 0.0
            V6 = 0.0
            if self._nz != 1:
                V6 = self.potential_real(x, y, zp)
                V5 = self.potential_real(x, y, zm)
            Ex = (V1 - V2) / (xp - xm)
            Ey = (V3 - V4) / (yp - ym)
            Ez = (self._nz != 1) and (V5 - V6) / (zp - zm) or 0.0

            if self._field_type == 'magnetic':
                Ex *= self._ng
                Ey *= self._ng
                Ez *= self._ng
            return (Ex, Ey, Ez)

    def point(self, x, y, z=0, is_electrode = None, potential=None):
        """
=head3 point

  (is_electrode, potential) = pa.point(x, y, z)
  pa.point(x, y, z, is_electrode, potential)

Gets or sets the Boolean electrode state and the potential
at the given integer point.

This is identical to calls
to both the potential and electrode methods.  Dies on error.

  pa.point(10, 20, 30, 1, 2.15)
  (is_electrode, potential) = pa.point(10, 20, 30)

The first line above is the same as

  pa.electrode(10, 20, 30, 1)
  pa.potential(10, 20, 30, 2.15)

=over

=item C<x> - integer containing x position in grid points.

=item C<y> - integer containing y position in grid points.

=item C<z> - integer containing z position in grid points.

=item C<is_electrode> - Boolean indicating whether the point is an electrode
(if setting).

=item C<potential> - real number containing the potential value (if setting).

=back

Returns: (is_electrode, potential) tuple (if getting).

=cut
        """
        assert self.inside(x,y,z), self._fail_point(x,y,z)

        pos = (z * self._ny + y) * self._nx + x

        if is_electrode != None and potential == None: potential = 0.0

        if is_electrode == None:
            potential = self._points[pos]
            is_electrode = (potential > self._max_voltage)
            if is_electrode: potential -= 2 * self._max_voltage
            return (is_electrode, potential)
        else:
            if potential > self._max_voltage:
                self.max_voltage(potential * 2.0)
            self._points[pos] = potential
            if is_electrode: self._points[pos] += 2 * self._max_voltage

    def potential(self, x, y, z=0, potential=None):
        """
=head3 potential

  potential = pa.potential(x, y, z)
  pa.potential(x, y, z, potential)

Gets or sets the potential at the given integer point.

  pa.potential(10, 20, 30, 2.15)
  print pa.potential(10, 20, 30)

=over

=item C<x> - integer containing x position in grid points.

=item C<y> - integer containing y position in grid points.

=item C<z> - integer containing z position in grid points.

=item C<potentials> - real number containing potential value (if setting).

=back

Returns: potential (if getting).

=cut
        """
        assert self.inside(x,y,z), self._fail_point(x,y,z)

        pos = (z * self._ny + y) * self._nx + x
        is_electrode = (self._points[pos] > self._max_voltage)

        if potential == None:
            val = self._points[pos]
            if is_electrode: val -= 2 * self._max_voltage
            return val
        else:
            if potential > self._max_voltage:
                self.max_voltage(potential * 2.0)
            self._points[pos] = potential
            if is_electrode: self._points[pos] += 2 * self._max_voltage

    #FIX? rename? potential_real --> potential, and potential --> potential_int ?
    def potential_real(self, x, y, z=0):
        """
=head3 potential_real

  potential = pa.potential_real(x, y, z)

Get the potential at the given real point, taking symmetry and mirroring
into account.

Interpolation is applied
between grid points, as described in Appendix H of the SIMION 8
manual (or Appendix E of the SIMION 7 manual),
except that the current version of this module does not
perform special handling near electrode edges.

  print pa.potential(10.3, 20.2, 30.7)

=over

=item C<x> - real number containing x position in grid points.

=item C<y> - real number containing y position in grid points.

=item C<z> - real number containing z position in grid points.

=back

Returns: real number containing interpolated potential value.

=cut
        """
        assert self.inside_real(x,y,z), self._fail_point(x,y,z)

        xeff = abs(x)  # if mirroring
        yeff = abs(y)
        zeff = abs(z)

        p = 0.0
        if self._symmetry == 'planar':
            if self._nz == 1: # 2D
                xi = int(xeff)
                yi = int(yeff)

                wx = xeff - xi
                wy = yeff - yi
                # note the checks on wx and wy to protect against cases where
                # xi + 1 == nx or yi + 1 == ny.
                p = \
                    (1-wx) * (1-wy) *              self.potential(xi,   yi,   0) + \
                       wx  * (1-wy) * ((wx != 0) and self.potential(xi+1, yi,   0) or 0.0) + \
                    (1-wx) *    wy  * ((wy != 0) and self.potential(xi,   yi+1, 0) or 0.0) + \
                       wx  *    wy  * ((wx != 0 and \
                                        wy != 0) and self.potential(xi+1, yi+1, 0) or 0.0)
                
            else: # 3D
                xi = int(xeff)
                yi = int(yeff)
                zi = int(zeff)

                wx = xeff - xi
                wy = yeff - yi
                wz = zeff - zi

                # note the checks on wx, wy, and wz to protect against cases where
                # xi + 1 == nx, yi + 1 == ny, or zi + 1 == nz.
                p = \
                    (1-wx)*(1-wy)*(1-wz)*self.potential(xi, yi, zi) + \
                       wx *(1-wy)*(1-wz)*((wx != 0) and self.potential(xi+1, yi,   zi) or 0.0) + \
                    (1-wx)*   wy *(1-wz)*((wy != 0) and self.potential(xi,   yi+1, zi) or 0.0) + \
                       wx *   wy *(1-wz)*((wx != 0 and \
                                           wy != 0) and self.potential(xi+1, yi+1, zi) or 0.0) + \
                    (1-wx)*(1-wy)*   wz *((wz != 0) and self.potential(xi  , yi, zi+1) or 0.0) + \
                       wx *(1-wy)*   wz *((wx != 0 and \
                                           wz != 0) and self.potential(xi+1, yi,   zi+1) or 0.0) + \
                    (1-wx)*   wy *   wz *((wy != 0 and \
                                           wz != 0) and self.potential(xi,   yi+1, zi+1) or 0.0) + \
                       wx *   wy *   wz *((wx != 0 and \
                                           wy != 0 and \
                                           wz != 0) and self.potential(xi+1, yi+1, zi+1) or 0.0) \
                 
        elif self._symmetry == 'cylindrical':
            r = sqrt(y*y + z*z)

            xi = int(xeff)
            ri = int(r)
            wx = xeff - xi
            wr = r - ri
            # note the checks on wx and wr to protect against cases where
            # xi + 1 == nx or ri + 1 == nr.
            p = \
                (1-wx) * (1-wr) * self.potential(xi, ri, 0) + \
                   wx  * (1-wr) * ((wx != 0) and self.potential(xi+1, ri,   0) or 0.0) + \
                (1-wx) *    wr  * ((wr != 0) and self.potential(xi,   ri+1, 0) or 0.0) + \
                   wx  *    wr  * ((wx != 0 and \
                                    wr != 0) and self.potential(xi+1, ri+1, 0) or 0.0)

        else: assert 0, "internal error: bad symmetry (" + self._symmetry + ")"

        return p

    def solid(self, x, y, z=0, is_electrode=None):
        """
=head3 solid

  is_solid = pa.solid(x, y, z)
  pa.solid(x, y, z, is_solid)

Gets or sets the solid electrode state for the given
integer voxel.

For a voxel to be a solid electrode (rather than a
ideal grid electrode), all four (for 2D arrays) or eight (for 3D
arrays) surrounding grid points must be electrode points.  Dies on
error.

  pa.solid(10, 20, 30, 1)
  print pa.solid(10, 20, 30)

=over

=item C<x> - integer containing x position in grid points.

=item C<y> - integer containing y position in grid points.

=item C<z> - integer containing z position in grid points.

=item C<is_solid> - Boolean indicating whether voxel is a solid
electrode point (if setting)

=back

Returns: is_solid (if getting)

=cut
        """

        assert self.voxel_inside(x,y,z), \
            "voxel (" + str(x) + "," + str(y) + "," + str(z) + ") out of bounds."

        if is_electrode == None:
            if self._nz == 1: # 2D planar or cylindrical
                electrode = \
                    self.electrode(x,   y,   z) and \
                    self.electrode(x+1, y,   z) and \
                    self.electrode(x,   y+1, z) and \
                    self.electrode(x+1, y+1, z)
                return electrode
            else: # 3D
                electrode = \
                    self.electrode(x,   y,   z) and \
                    self.electrode(x+1, y,   z) and \
                    self.electrode(x,   y+1, z) and \
                    self.electrode(x+1, y+1, z) and \
                    self.electrode(x,   y,   z+1) and \
                    self.electrode(x+1, y,   z+1) and \
                    self.electrode(x,   y+1, z+1) and \
                    self.electrode(x+1, y+1, z+1)
                return electrode
        else: # set
            if self._nz == 1: # 2D planar or cylindrical
                self.electrode(x,   y,   z, is_electrode)
                self.electrode(x+1, y,   z, is_electrode)
                self.electrode(x,   y+1, z, is_electrode)
                self.electrode(x+1, y+1, z, is_electrode)
            else: # 3D
                self.electrode(x,   y,   z,   is_electrode)
                self.electrode(x+1, y,   z,   is_electrode)
                self.electrode(x,   y+1, z,   is_electrode)
                self.electrode(x+1, y+1, z,   is_electrode)
                self.electrode(x,   y,   z+1, is_electrode)
                self.electrode(x+1, y,   z+1, is_electrode)
                self.electrode(x,   y+1, z+1, is_electrode)
                self.electrode(x+1, y+1, z+1, is_electrode)


    def raw(self, x, y, z=0, val=None):
        """
=head3 raw

  val = pa.raw(x, y, z)
  pa.raw(x, y, z, val)

Gets or sets the raw value at the given integer point.

The raw value is what is stored internally in the array
at each data point and is not normally used directly.
It is defined as potential(x,y,z) + is_electrode(x,y,z)
? 2 * max_voltage() : 0.

  pa.raw(10, 20, 30, 100002.15)
  print pa.raw(10, 20, 30)

=over

=item C<x> - integer containing x position in grid points.

=item C<y> - integer containing y position in grid points.

=item C<z> - integer containing z position in grid points.

=back

Returns: real number containing raw value.

=cut
        """
        assert self.inside(x,y,z), self._fail_point(x,y,z)

        pos = (z * self._ny + y) * self._nx + x

        if val == None:
            return self._points[pos]
        else:
            self._points[pos] = val


    # Group: Checkers

    def check(
        self,
        mode            = None,
        field_type      = None,
        symmetry        = None,
        mirror          = None,       
        mirror_x        = None,
        mirror_y        = None,
        mirror_z        = None,
        nx              = None,
        ny              = None,
        nz              = None,
        fast_adjustable = None,
        max_voltage     = None,
        ng              = None,
        dx_mm           = None,
        dy_mm           = None,
        dz_mm           = None,
        enable_points   = None,
        file            = None
    ):
        """
=head3 check

  $is_val = pa.check(...)

Checks whether the given combination of attributes is valid.

Any subset of the above named parameters may be specified, and
the named parameter 'mirror' containing a subset of the string
'xyz' may be specified as an alternative to the mirror_x,
mirror_y, and mirror_z named parameters.  The set method is
useful in cases when the attributes are interdependent.  For
example, all of these fail:

  if not util.check(symmetry = 'cylindrical', nz = 2):
      print util.error()
  if not util.check(mirror_z = 1, nz = 1):
      print util.error()
  if not util.check(symmetry = 'cylindrical, mirror = 'xz'):
      print util.error()

Refer to the individual 'check' functions for details on the parameters.

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """


        if mode != None and not self.check_mode(mode):
            return 0
        if symmetry != None and not self.check_symmetry(symmetry):
            return 0
        if max_voltage != None and not self.check_max_voltage(max_voltage):
            return 0
        if field_type != None and not self.check_field_type(field_type):
            return 0
        if ng != None and not self.check_ng(ng):
            return 0
        if nx != None and not self.check_nx(nx):
            return 0
        if ny != None and not self.check_ny(ny):
            return 0
        if nz != None and not self.check_nz(nz):
            return 0
        if nx != None and not self.check_size(nx, ny, nz):
            return 0
        if dx_mm != None and not self.check_dx_mm(dx_mm):
            return 0
        if dy_mm != None and not self.check_dy_mm(dy_mm):
            return 0
        if dz_mm != None and not self.check_dz_mm(dz_mm):
            return 0

        # aliases
        if mirror != None:
            if mirror_x != None:
                self._error = "mirror and mirror_x named parameters cannot coexist."
                return 0
            if mirror_y != None:
                self._error = "mirror and mirror_y named parameters cannot coexist."
                return 0
            if mirror_z != None:
                self._error = "mirror and mirror_z named parameters cannot coexist."
                return 0

            (mirror_x, mirror_y, mirror_z) = self._parse_mirror(mirror)

        if symmetry == 'cylindrical' and mirror_y == 0:
            self._error = "y mirroring must be enabled under cylindrical symmetry."
            return 0

        if symmetry == 'cylindrical' and nz != 1 and nz != None:
            self._error = "nz (" + str(nz) + ") must be 1 under cylindrical symmetry."
            return 0
        if mirror_z and nz == 1:
            self._error = "nz (" + str(nz) + ") cannot be 1 under z mirroring."
            return 0

        return 1

    def check_field_type(self, field_type):
        """
=head3 check_field_type

  is_val = pa.check_field_type(field_type)

Checks whether the given field type is valid.

Example:

  if not util.check_field_type("magnetic"): print util.error()

=over

=item C<field_type> - string containing field type identifier.  Valid
identifiers are "electrostatic" and "magnetic".

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if field_type not in ['electrostatic', 'magnetic']:
            self._error = "Field type (" + field_type + \
                     ") must be 'electrostatic' or 'magnetic'."
            return 0
        return 1

    def check_max_voltage(self, max_voltage):
        """
=head3 check_max_voltage

  is_val = pa.check_max_voltage(voltage)

Checks whether the given max voltage values is valid.

Example:

  if not util.check_max_voltage(100000): print util.error()

=over

=item C<max_voltage> - number containiner votlage value.

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if max_voltage < 0:  #ok?
            self._error = "Max voltage (" + str(max_voltage) + ") is out of range."
            return 0
        return 1

    def check_mirror(self, mirror):
        """
=head3 check_mirror

  is_val = pa.check_mirror(mirror)

Check whether the given mirroring string is valid.

  if not util.check_mirror("yz"): print util.error()

=over

=item C<mirrors> - string containing the mirroring identifier.  Valid
strings are an ordered subset of "xyz".

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        m = re.match('^x?y?z?$', mirror)
        if m == None:
            self._error = "Mirror string (" + mirror + ") invalid."
            return 0
        return 1

    def check_mode(self, mode):
        """
=head3 check_mode

  is_val = pa.check_mode(mode)

Checks whether the given mode is valid.

Example:

  if not util.check_mode(-1): print util.error()

=over

=item C<mode> - integer mode number.

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if mode != -1 and mode != -2:
            self._error = "Mode (" + str(mode) + ") is out of range."
            return 0
        return 1

    def check_ng(self, ng):
        """
=head3 check_ng

  is_val = pa.check_ng(ng)

Checks whether the given ng magnetic scaling factor is valid.

Example:

  if not util.check_ng(100): print util.error()

=over

=item C<ng> - integer containing ng number

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if ng < 0:
            self._error = "Magnetic scaling factor (" + str(ng) + \
                     ") must be no less than 0."
            return 0
        return 1

    def check_nx(self, nx):
        """
=head3 check_nx

  is_val = pa.check_nx(nx)

Checks whether the given grid dimension in the x direction is valid.

Example:

  if not util.check_nx(100): print util.error()

=over

=item C<nx> - integer containing x dimension in number of grid points.

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if nx < 3:
            self._error = "nx value (" + str(nx) + ") must be no less than 3."
            return 0
        if nx > 90000:
            self._error = "nx value (" + str(nx) + ") must be no greater than 90000."
            return 0
        return 1


    def check_ny(self, ny):
        """
=head3 check_ny

  is_val = pa.check_ny(ny)

Checks whether the given grid dimension in the y direction is valid.

Example:

  if not util.check_ny(100): print util.error()

=over

=item C<ny> - integer containing y dimension in number of grid points.

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if ny < 3:
            self._error = "ny value (" + str(ny) + ") must be no less than 3."
            return 0
        if ny > 90000:
            self._error = "ny value (" + str(ny) + ") must be no greater than 90000."
            return 0
        return 1

    def check_nz(self, nz):
        """
=head3 check_nz

  is_val = pa.check_nz(nz)

Checks whether the given grid dimension in the z direction is valid.

Example:

  if not util.check_nz(100): print util.error()

=over

=item C<nz> - integer containing z dimension in number of grid points.

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if nz < 1:
            self._error = "nz value (" + str(nz) + ") must be no less than 1."
            return 0
        if nz > 90000:
            self._error = "nz value (" + str(nz) + ") must be no greater than 90000."
            return 0
        return 1

    def check_size(self, nx, ny, nz = 1):
        """
=head3 check_size

  is_val = pa.check_size(nx, ny, nz)

Checks whether the given set of grid dimensions
in the x, y, and z directions is valid as a whole.

Note that check_nx(nx) and check_ny(ny) and check_nz(nz) implies
check_size(nx, ny, nz), although the converse is not necessarily
true.  Example:

  if not util.check_size(3, 3, 1): print util.error()

=over

=item C<nx> - integer containing x dimension in number of grid points.

=item C<ny> - integer containing y dimension in number of grid points.

=item C<nz> - integer containing z dimension in number of grid points.

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """

        if not self.check_nx(nx): return 0
        if not self.check_ny(ny): return 0
        if not self.check_nz(nz): return 0

        if nx * ny * nz > 200000000:
            self._error =  "(" + str(nx) + "," + str(ny) + "," + str(nz) + \
                      ") exceeds 200 million points."
            return 0
        return 1


    def check_symmetry(self, symmetry):
        """
=head3 check_symmetry

  is_val = pa.check_symmetry(symmetry)

Checks whether the given symmetry is valid.

Example:

  if not util.check_symmetry("cylindrical"): print util.error()

=over

=item C<symmetry> - string containing symmetry identifier.
Valid strings include "planar" and "cylindrical".

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if symmetry not in ["planar", "cylindrical"]:
            self._error = "Symmetry (" + symmetry + ") must be 'planar' or 'cylindrical'."
            return 0
        return 1

    def check_dx_mm(self, xmmgu):
        """
=head3 check_dx_mm

  is_val = pa.check_dx_mm(xmmgu)

Checks whether the given grid unit size in the x direction is valid.

Example:

  if not util.check_dx_mm(1): print util.error()

=over

=item C<xmmgu> - double containing size in mm

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if xmmgu < 1e-6:
            self._error = "dx_mm value (" + str(xmmgu) + ") must be no less than 1e-6."
            return 0
        if xmmgu > 900:
            self._error = "dx_mm value (" + str(xmmgu) + ") must be no greater than 900."
            return 0
        return 1

    def check_dy_mm(self, ymmgu):
        """
=head3 check_dy_mm

  is_val = pa.check_dy_mm(ymmgu)

Checks whether the given grid unit size in the y direction is valid.

Example:

  if not util.check_dy_mm(1): print util.error()

=over

=item C<ymmgu> - double containing size in mm

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if ymmgu < 1e-6:
            self._error = "dy_mm value (" + str(ymmgu) + ") must be no less than 1e-6."
            return 0
        if ymmgu > 900:
            self._error = "dy_mm value (" + str(ymmgu) + ") must be no greater than 900."
            return 0
        return 1

    def check_dz_mm(self, zmmgu):
        """
=head3 check_dz_mm

  is_val = pa.check_dz_mm(zmmgu)

Checks whether the given grid unit size in the z direction is valid.

Example:

  if not util.check_dz_mm(1): print util.error()

=over

=item C<zmmgu> - double containing size in mm

=back

Returns: (ok, err), where ok is a Boolean indicating validity, and
err is a string containing any error message.

=cut
        """
        if zmmgu < 1e-6:
            self._error = "dz_mm value (" + str(zmmgu) + ") must be no less than 1e-6."
            return 0
        if zmmgu > 900:
            self._error = "dz_mm value (" + str(zmmgu) + ") must be no greater than 900."
            return 0
        return 1

    # Group: Error Handling

    def error(self):
        """
=head3 error

  s = pa.error()

Get last error message generated by one of the check calls.

=cut
        """
        return self._error;



    def _parse_mirror(self, mirror):
        m = re.match('^(x?)(y?)(z?)$', mirror)
        assert m != None, "Invalid mirroring (" + mirror + ")."
        return (m.group(1) != '', m.group(2) != '', m.group(3) != '')

    def _inside_cylindrical_real(self, x, r):
        yes = 1
        if x >= 0.0:
            yes = (x <= self._nx-1)
        elif self.mirror_x():
            yes = (-x <= self._nx-1)
        else:
            yes = 0
        if yes:
            yes = (r <= self._ny - 1)
        return yes

    def _set_field(self, x, y, z, field_x, field_y, field_z=0):
        # perform numerical integration to solve the following for V:
        #
        #   E = - grad(V)
        #
        # This is done by the line integral:
        #
        #   V(x,y,z) = V(0,0,0) + line_integral_{C} E * n ds
        #
        # where C is an arbitrary path from (0,0,0) to (x,y,z).  For
        # each point (x,y,z), we actually do a weighted average of all
        # lattice paths (0,0,0) to (x,y,z) of length x+y+z.  In this
        # algorithm, the trapezoidal rule is used for the numerical
        # integration due to a nice algorithm requiring only O(1)
        # additional memory usage.
        #
        # Currently, V(0,0,0) is assumed to be zero.
        is_electrode = 0

        if self.field_type() == 'magnetic':
            field_x /= self.ng()
            field_y /= self.ng()
            field_z /= self.ng()

        if x != self.nx() - 1:
            self.point(x + 1, y, z, 0,
                       self.raw(x + 1, y, z) - field_x)
        if y != self.ny() - 1:
            self.point(x, y + 1, z, 0,
                       self.raw(x, y + 1, z) - field_y)
        if z != self.nz() - 1:
            self.point(x, y, z + 1, 0,
                       self.raw(x, y, z + 1) - field_z)

        if x != 0 and y != 0 and z != 0:
            val = \
                (self.potential(x-1, y,   z) + \
                 self.potential(x,   y-1, z) + \
                 self.potential(x,   y,   z-1)) / 3.0 + \
                (self.raw(x,   y,   z) - \
                 field_x - field_y - field_z) / 6.0
            
            self.point(x, y, z, is_electrode, val)
        elif x != 0 and y != 0: # z == 0
            val = \
                (self.potential(x-1, y,   z) + \
                 self.potential(x,   y-1, z)) / 2.0 + \
                (self.raw(x,   y,   z) - \
                 field_x - field_y) / 4.0
            
            self.point(x, y, z, is_electrode, val)
        elif x != 0 and z != 0: # y == 0
            val = \
                (self.potential(x-1, y,   z) + \
                 self.potential(x,   y,   z-1)) / 2.0 + \
                (self.raw(x,   y,   z) - \
                 field_x - field_z) / 4.0
            
            self.point(x, y, z, is_electrode, val)
        elif y != 0 and z != 0: # x == 0
            val = \
                (self.potential(x,   y-1, z) + \
                 self.potential(x,   y,   z-1)) / 2.0 + \
                (self.raw(x,   y,   z) - \
                 field_y - field_z) / 4.0
            
            self.point(x, y, z, is_electrode, val)
        elif z != 0: # x == 0 and y == 0
            val = \
                 self.potential(x,   y,   z-1) + \
                (self.raw(x,   y,   z) - \
                 field_z) / 2.0
            
            self.point(x, y, z, is_electrode, val)
        elif y != 0: # x == 0 and z == 0
            val = \
                 self.potential(x,   y-1, z) + \
                (self.raw(x,   y,   z) - \
                 field_y) / 2.0
            
            self.point(x, y, z, is_electrode, val)
        elif x != 0: # y == 0 and z == 0
            val = \
                 self.potential(x-1, y,   z) + \
                (self.raw(x,   y,   z) - \
                 field_x) / 2.0
            
            self.point(x, y, z, is_electrode, val)
        else: # x == 0 and y == 0 and z == 0
            self.point(x, y, z, is_electrode, 0)

        #print "DEBUG:point=", self.potential(x, y, z), "\n"

    def _fail_point(self, x, y, z):
        return "point (" + str(x) + "," + str(y) + "," + str(z) + \
            ") out of bounds (" + \
            str(self._nx) + "," + str(self._ny) + "," + str(self._nz) + ")."

"""
=head1 CHANGES

 2009-02-18
  Python 3000 compatibility < http://simion.com/issue/524 >

 2010-01-25
  Add support for mode -2 PA files (SIMION 8.1 anisotropic scaling
    x_mm_per_gu/y_mm_per_gu/z_mm_per_gu).
  load/save methods now raise a PAError exception on failure.
  Remove old FIX comments.
  
 2011-08-11
  Renamed x_mm_per_gu,y_mm_per_gu,z_mm_per_gu -> dx_mm/dy_mm/dz_mm

=head1 SOURCE

David Manura (c) 2003-2011 Scientific Instrument Services, Inc.
Licensed under the terms of SIMION 8.0/8.1 or the SIMION SL Toolkit.
Created 2003-11.

version: 20110811

=cut
"""

# SIMION.PA (Python)
# This module is documented in the SIMION supplemental documentation.
# (c) 2003-2011 Scientific Instrument Services, Inc. (SIMION 8.0/8.1 License)
