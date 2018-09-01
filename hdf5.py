"""
Demonstrates basic interaction with HDF5 library using python / ctypes
"""
import ctypes


# load library (this would be platform-dependent)
hdf5 = ctypes.cdll.LoadLibrary('libhdf5.so')

# Define constants
hid_t = ctypes.c_int64
herr_t = ctypes.c_int
htri_t = ctypes.c_int
size_t = ctypes.c_ulong
H5F_ACC_RDONLY = ctypes.c_uint(0)
H5P_DEFAULT = hid_t(0)

H5T_NO_CLASS = -1
H5T_INTEGER = 0
H5T_FLOAT = 1
H5T_TIME = 2
H5T_STRING = 3
H5T_BITFIELD = 4
H5T_OPAQUE = 5
H5T_COMPOUND = 6
H5T_REFERENCE = 7
H5T_ENUM = 8
H5T_VLEN = 9
H5T_ARRAY = 10

# set function signatures

# hid_t H5Fopen(const char *filename, unsigned flags, hid_t access_plist)
hdf5.H5Fopen.argtypes = [ctypes.c_char_p, ctypes.c_uint, hid_t]
hdf5.H5Fopen.restype = hid_t
# hid_t H5Dopen1(hid_t file_id, const char *name)
hdf5.H5Dopen1.argtypes = [hid_t, ctypes.c_char_p]
hdf5.H5Dopen1.restype = hid_t
# hid_t H5Aopen_name (hid_t loc_id, const char *name)
hdf5.H5Aopen_name.argtypes = [hid_t, ctypes.c_void_p]
hdf5.H5Aopen_name.restype = hid_t
# hid_t H5Aget_space (hid_t attr_id) 
hdf5.H5Aget_space.argtypes = [hid_t]
hdf5.H5Aget_space.restype = ctypes.c_int32#hid_t
# hid_t H5Aget_type (hid_t attr_id) 
hdf5.H5Aget_type.argtypes = [hid_t]
hdf5.H5Aget_type.restype = hid_t
# H5T_class_t H5Tget_class(hid_t type_id)
hdf5.H5Tget_class.argtypes = [hid_t]
hdf5.H5Tget_class.restype = ctypes.c_int
# size_t H5Tget_size(hid_t type_id)
hdf5.H5Tget_size.argtypes = [hid_t]
hdf5.H5Tget_size.restype = size_t
# herr_t H5Aread(hid_t attr_id, hid_t type_id, void *buf)
hdf5.H5Aread.argtypes = [hid_t, hid_t, ctypes.c_void_p]
hdf5.H5Aread.restype = herr_t
# herr_t H5Aclose (hid_t attr_id)
hdf5.H5Aclose.argtypes = [hid_t]
hdf5.H5Aclose.restype = herr_t
# htri_t H5Tis_variable_str(hid_t type_id)
hdf5.H5Tis_variable_str.argtypes = [hid_t]
hdf5.H5Aclose.restype = htri_t
# int H5Sget_simple_extent_ndims(hid_t space_id);
hdf5.H5Sget_simple_extent_ndims.argtypes = [ctypes.c_int32]#[hid_t]
hdf5.H5Sget_simple_extent_ndims.restype = ctypes.c_int


def open_file(filename):
    """Open an HDF5 file and return the handle.
    """
    hdf5.H5open()
    return hdf5.H5Fopen(filename, H5F_ACC_RDONLY, H5P_DEFAULT)

def get_dataset(h5file, ds_name):
    """Return the handle to a dataset given an HDF5 file handle.
    """
    return hdf5.H5Dopen1(h5file, ds_name)

def read_str_attribute(location, attr_name):
    """Return the value of a fixed-length string attribute given its
    location (group / dataset) and name.
    """
    if isinstance(attr_name, unicode):
        attr_name = bytes(attr_name)
    # read attribute
    attr = hdf5.H5Aopen_name(location, attr_name)
    atype  = hdf5.H5Aget_type(attr)
    # aspace  = hdf5.H5Aget_space(attr)

    type_class = hdf5.H5Tget_class(atype)
    assert type_class == H5T_STRING, "Attribute type is not string (class=%d)" % type_class
    assert hdf5.H5Tis_variable_str(atype) == 0, "Attribute is not fixed-length string type"

    size = hdf5.H5Tget_size(atype)
    buf = ctypes.create_string_buffer(size)
    ret = hdf5.H5Aread(attr, atype, ctypes.byref(buf))

    hdf5.H5Aclose(attr)

    return buf.value
