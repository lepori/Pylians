import numpy as np
import time,sys,os
cimport numpy as np
cimport cython
from libc.math cimport sqrt,pow,sin,floor

################################################################################
################################# ROUTINES #####################################
# NGP(pos,number,BoxSize)
# CIC(pos,number,BoxSize)
# NGPW(pos,number,BoxSize,W)
# CICW(pos,number,BoxSize,W)
################################################################################
################################################################################



################################################################################
# This function computes the density field of a cubic distribution of particles
# pos ------> positions of the particles. Numpy array
# number ---> array with the density field. Numpy array (dims,dims,dims)
# BoxSize --> Size of the box
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef np.ndarray[np.float32_t,ndim=2] CIC(np.ndarray[np.float32_t,ndim=2] pos,
                                          np.ndarray[np.float32_t,ndim=3] number,
                                          float BoxSize):
    cdef int axis,dims
    cdef long i,particles
    cdef float inv_cell_size,dist
    cdef np.ndarray[np.float32_t,ndim=1] u,d
    cdef np.ndarray[np.int32_t,  ndim=1] index_d,index_u
    
    # find number of particles, the inverse of the cell size and dims
    particles = len(pos);  dims = len(number);  inv_cell_size = dims/BoxSize
    
    # define arrays
    u       = np.zeros(3,dtype=np.float32) #for up
    d       = np.zeros(3,dtype=np.float32) #for down
    index_u = np.zeros(3,dtype=np.int32)
    index_d = np.zeros(3,dtype=np.int32)
    
    # do a loop over all particles
    for i in xrange(particles):

        # $: grid point, X: particle position
        # $.........$..X......$
        # ------------>         dist    (1.3)
        # --------->            index_d (1)
        # --------------------> index_u (2)
        #           --->        u       (0.3)
        #              -------> d       (0.7)
        for axis in xrange(3):
            dist          = pos[i,axis]*inv_cell_size
            u[axis]       = dist - <int>dist
            d[axis]       = 1.0 - u[axis]
            index_d[axis] = (<int>dist)%dims
            index_u[axis] = index_d[axis] + 1
            index_u[axis] = index_u[axis]%dims #seems this is faster

        number[index_d[0],index_d[1],index_d[2]] += d[0]*d[1]*d[2]
        number[index_d[0],index_d[1],index_u[2]] += d[0]*d[1]*u[2]
        number[index_d[0],index_u[1],index_d[2]] += d[0]*u[1]*d[2]
        number[index_d[0],index_u[1],index_u[2]] += d[0]*u[1]*u[2]
        number[index_u[0],index_d[1],index_d[2]] += u[0]*d[1]*d[2]
        number[index_u[0],index_d[1],index_u[2]] += u[0]*d[1]*u[2]
        number[index_u[0],index_u[1],index_d[2]] += u[0]*u[1]*d[2]
        number[index_u[0],index_u[1],index_u[2]] += u[0]*u[1]*u[2]
        
    return number
################################################################################

################################################################################
# This function computes the density field of a cubic distribution of particles
# using weights
# pos ------> positions of the particles. Numpy array
# number ---> array with the density field. Numpy array (dims,dims,dims)
# BoxSize --> Size of the box
# W --------> weights of the particles
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef np.ndarray[np.float32_t,ndim=2] CICW(np.ndarray[np.float32_t,ndim=2] pos,
                                           np.ndarray[np.float32_t,ndim=3] number,
                                           float BoxSize,
                                           np.ndarray[np.float32_t,ndim=1] W):
    cdef int axis,dims
    cdef long i,particles
    cdef float inv_cell_size,dist
    cdef np.ndarray[np.float32_t,ndim=1] u,d
    cdef np.ndarray[np.int32_t,  ndim=1] index_d,index_u
    
    # find number of particles, the inverse of the cell size and dims
    particles = len(pos);  dims = len(number);  inv_cell_size = dims/BoxSize
    
    # define arrays
    u       = np.zeros(3,dtype=np.float32) #for up
    d       = np.zeros(3,dtype=np.float32) #for down
    index_u = np.zeros(3,dtype=np.int32)
    index_d = np.zeros(3,dtype=np.int32)
    
    # do a loop over all particles
    for i in xrange(particles):

        # $: grid point, X: particle position
        # $.........$..X......$
        # ------------>         dist    (1.3)
        # --------->            index_d (1)
        # --------------------> index_u (2)
        #           --->        u       (0.3)
        #              -------> d       (0.7)
        for axis in xrange(3):
            dist          = pos[i,axis]*inv_cell_size
            u[axis]       = dist - <int>dist
            d[axis]       = 1.0 - u[axis]
            index_d[axis] = (<int>dist)%dims
            index_u[axis] = index_d[axis] + 1
            index_u[axis] = index_u[axis]%dims #seems this is faster

        number[index_d[0],index_d[1],index_d[2]] += d[0]*d[1]*d[2]*W[i]
        number[index_d[0],index_d[1],index_u[2]] += d[0]*d[1]*u[2]*W[i]
        number[index_d[0],index_u[1],index_d[2]] += d[0]*u[1]*d[2]*W[i]
        number[index_d[0],index_u[1],index_u[2]] += d[0]*u[1]*u[2]*W[i]
        number[index_u[0],index_d[1],index_d[2]] += u[0]*d[1]*d[2]*W[i]
        number[index_u[0],index_d[1],index_u[2]] += u[0]*d[1]*u[2]*W[i]
        number[index_u[0],index_u[1],index_d[2]] += u[0]*u[1]*d[2]*W[i]
        number[index_u[0],index_u[1],index_u[2]] += u[0]*u[1]*u[2]*W[i]
        
    return number
################################################################################

################################################################################
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef np.ndarray[np.float32_t,ndim=2] NGP(np.ndarray[np.float32_t,ndim=2] pos,
                                          np.ndarray[np.float32_t,ndim=3] number,
                                          float BoxSize):
    cdef int axis,dims
    cdef long i,particles
    cdef float inv_cell_size
    cdef np.ndarray[np.int32_t,  ndim=1] index
    
    # find number of particles, the inverse of the cell size and dims
    particles = len(pos);  dims = len(number);  inv_cell_size = dims/BoxSize
    index = np.zeros(3,dtype=np.int32)

    # do a loop over all particles
    for i in xrange(particles):
        for axis in xrange(3):
            index[axis] = <int>(pos[i,axis]*inv_cell_size + 0.5)
            index[axis] = index[axis]%dims
        number[index[0],index[1],index[2]] += 1.0

    return number

################################################################################

################################################################################
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(True)
cpdef np.ndarray[np.float32_t,ndim=2] NGPW(np.ndarray[np.float32_t,ndim=2] pos,
                                           np.ndarray[np.float32_t,ndim=3] number,
                                           float BoxSize,
                                           np.ndarray[np.float32_t,ndim=1] W):
    cdef int axis,dims
    cdef long i,particles
    cdef float inv_cell_size
    cdef np.ndarray[np.int32_t,  ndim=1] index
    
    # find number of particles, the inverse of the cell size and dims
    particles = len(pos);  dims = len(number);  inv_cell_size = dims/BoxSize
    index = np.zeros(3,dtype=np.int32)

    # do a loop over all particles
    for i in xrange(particles):
        for axis in xrange(3):
            index[axis] = <int>(pos[i,axis]*inv_cell_size + 0.5)
            index[axis] = index[axis]%dims
        number[index[0],index[1],index[2]] += W[i]

    return number
################################################################################