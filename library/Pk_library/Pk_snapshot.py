import numpy as np
import readsnap
import redshift_space_library as RSL
import MAS_library as MASL
import units_library as UL
import Pk_library as PKL
import sys,os

########### routines ############
# Pk_comp(snapshot_fname,ptype,dims,do_RSD,axis,hydro,cpus)
# Pk_Gadget(snapshot_fname,dims,particle_type,do_RSD,axis,hydro,cpus)
#################################


U = UL.units();  rho_crit = U.rho_crit

# dictionary for files name
name_dict = {'0' :'GAS',  '01':'GCDM',  '02':'GNU',    '04':'Gstars',
             '1' :'CDM',                '12':'CDMNU',  '14':'CDMStars',
             '2' :'NU',                                '24':'NUStars',
             '4' :'Stars',
             '-1':'matter'}

###############################################################################
# This routine computes the power spectrum of either a single species or of all
# species from a Gadget routine
# snapshot_fname -----------> name of the Gadget snapshot
# ptype --------------------> scalar: 0-GAS, 1-CDM, 2-NU, 4-Stars, -1:ALL
# dims ---------------------> Total number of cells is dims^3 to compute Pk
# do_RSD -------------------> Pk in redshift-space (True) or real-space (False)
# axis ---------------------> axis along which move particles in redshift-space
# hydro --------------------> whether snapshot is hydro (True) or not (False)
# cpus ---------------------> Number of cpus to compute power spectra 
def Pk_comp(snapshot_fname,ptype,dims,do_RSD,axis,hydro,cpus):

    # read relevant paramaters on the header
    print 'Computing power spectrum...'
    head     = readsnap.snapshot_header(snapshot_fname)
    BoxSize  = head.boxsize/1e3 #Mpc/h
    Nall     = head.nall;  Ntotal = np.sum(Nall,dtype=np.int64)
    Omega_m  = head.omega_m
    Omega_l  = head.omega_l
    redshift = head.redshift
    Hubble   = 100.0*np.sqrt(Omega_m*(1.0+redshift)**3+Omega_l)  #km/s/(Mpc/h)
    z        = '%.3f'%redshift
        
    # read the positions of the particles
    pos = readsnap.read_block(snapshot_fname,"POS ",parttype=ptype)/1e3 #Mpc/h
    print '%.3f < X [Mpc/h] < %.3f'%(np.min(pos[:,0]),np.max(pos[:,0]))
    print '%.3f < Y [Mpc/h] < %.3f'%(np.min(pos[:,1]),np.max(pos[:,1]))
    print '%.3f < Z [Mpc/h] < %.3f\n'%(np.min(pos[:,2]),np.max(pos[:,2]))

    # read the velocities of the particles
    if do_RSD:
        print 'moving particles to redshift-space...'
        vel = readsnap.read_block(snapshot_fname,"VEL ",parttype=ptype) #km/s
        RSL.pos_redshift_space(pos,vel,BoxSize,Hubble,redshift,axis)
        del vel;  print 'done'

    # define delta array
    delta = np.zeros((dims,dims,dims),dtype=np.float32)

    # when dealing with all particles take into account their different masses
    if ptype==-1:
        if not(hydro):
            M = np.zeros(Ntotal,dtype=np.float32) #define the mass array
            offset = 0
            for ptype in [0,1,2,3,4,5]:
                M[offset:offset+Nall[ptype]] = Masses[ptype]
                offset += Nall[ptype]
        else:
            M = readsnap.read_block(snapshot_fname,"MASS",parttype=-1)*1e10
        
        mean = np.sum(M,dtype=np.float64)/dims3
        MASL.CICW(pos,delta,BoxSize,M); del pos,M

    else:  
        mean = len(pos)*1.0/dims3
        MASL.CIC(pos,delta,BoxSize); del pos

    # compute the P(k)
    delta /= mean;  delta -= 1.0
    [k,Pk0,Pk2,Pk4,Nmodes] = PKL.Pk(delta,BoxSize,axis=axis,MAS='CIC',
                                    threads=cpus);  del delta

    # write P(k) to output file
    fout = 'Pk_' + name_dict[str(ptype)]
    if do_RSD:  fout += ('_RS_axis=' + str(axis) + '_z=' + z + '.dat')
    else:       fout +=                           ('_z=' + z + '.dat')
    np.savetxt(fout,np.transpose([k,Pk0,Pk2,Pk4,Nmodes]))
###############################################################################

###############################################################################
# This routine computes the auto- and cross-power spectra of a Gadget snapshot
# in real or redshift-space. Can compute the total matter power spectrum or the
# auto- cross-power spectra of different particle types.
# If one only wants the total matter P(k), set particle_type=[-1]. If the P(k)
# of the different components is wanted set for instance particle_type=[0,1,4]
# snapshot_fname -----------> name of the Gadget snapshot
# dims ---------------------> Total number of cells is dims^3 to compute Pk
# particle_type ------------> compute Pk of those particles, e.g. [1,2]
# do_RSD -------------------> Pk in redshift-space (True) or real-space (False)
# axis ---------------------> axis along which move particles in redshift-space
# hydro --------------------> whether snapshot is hydro (True) or not (False)
# cpus ---------------------> Number of cpus to compute power spectra
def Pk_Gadget(snapshot_fname,dims,particle_type,do_RSD,axis,hydro,cpus):

    # for either one single species or all species use this routine
    if len(particle_type)==1:
        Pk_comp(snapshot_fname,particle_type[0],dims,do_RSD,axis,hydro,cpus)
        return None

    # read snapshot head and obtain BoxSize, Omega_m and Omega_L
    print '\nREADING SNAPSHOTS PROPERTIES'
    head     = readsnap.snapshot_header(snapshot_fname)
    BoxSize  = head.boxsize/1e3  #Mpc/h
    Nall     = head.nall
    Masses   = head.massarr*1e10 #Msun/h
    Omega_m  = head.omega_m
    Omega_l  = head.omega_l
    redshift = head.redshift
    Hubble   = 100.0*np.sqrt(Omega_m*(1.0+redshift)**3+Omega_l)  #km/s/(Mpc/h)
    h        = head.hubble
    z        = '%.3f'%redshift
    dims3    = dims**3

    # compute the values of Omega_cdm, Omega_nu, Omega_gas and Omega_s
    Omega_c = Masses[1]*Nall[1]/BoxSize**3/rho_crit
    Omega_n = Masses[2]*Nall[2]/BoxSize**3/rho_crit
    Omega_g, Omega_s = 0.0, 0.0
    if Nall[0]>0:
        if Masses[0]>0:  
            Omega_g = Masses[0]*Nall[0]/BoxSize**3/rho_crit
            Omega_s = Masses[4]*Nall[4]/BoxSize**3/rho_crit
        else:    
            # mass in Msun/h
            mass = readsnap.read_block(snapshot_fname,"MASS",parttype=0)*1e10 
            Omega_g = np.sum(mass,dtype=np.float64)/BoxSize**3/rho_crit
            mass = readsnap.read_block(snapshot_fname,"MASS",parttype=4)*1e10
            Omega_s = np.sum(mass,dtype=np.float64)/BoxSize**3/rho_crit
            del mass

    # some verbose
    print 'Omega_gas    = ',Omega_g
    print 'Omega_cdm    = ',Omega_c
    print 'Omega_nu     = ',Omega_n
    print 'Omega_star   = ',Omega_s
    print 'Omega_m      = ',Omega_g + Omega_c + Omega_n + Omega_s
    print 'Omega_m snap = ',Omega_m

    # dictionary giving the value of Omega for each component
    Omega_dict = {0:Omega_g, 1:Omega_c, 2:Omega_n, 4:Omega_s}
    #####################################################################

    # define the array containing the deltas
    delta = [[],[],[],[]]  #array containing the gas, CDM, NU and stars deltas

    # dictionary among particle type and the index in the delta and Pk arrays
    # delta of stars (ptype=4) is delta[3] not delta[4]
    index_dict = {0:0, 1:1, 2:2, 4:3} 

    # define suffix here
    if do_RSD:  suffix = '_RS_axis=' + str(axis) + '_z=' + z + '.dat'
    else:       suffix =                           '_z=' + z + '.dat'
    #####################################################################

    # do a loop over all particle types and compute the deltas
    for ptype in particle_type:
    
        # read particle positions in #Mpc/h
        pos = readsnap.read_block(snapshot_fname,"POS ",parttype=ptype)/1e3 

        # move particle positions to redshift-space
        if do_RSD:
            vel = readsnap.read_block(snapshot_fname,"VEL ",parttype=ptype)#km/s
            RSL.pos_redshift_space(pos,vel,BoxSize,Hubble,redshift,axis)
            del vel

        # find the index of the particle type in the delta array
        index = index_dict[ptype]

        # compute mean number of particles per grid cell
        mean_number = len(pos)*1.0/dims3

        # compute the deltas
        delta[index] = np.zeros((dims,dims,dims),dtype=np.float32)
        MASL.CIC(pos,delta[index],BoxSize);  del pos
        delta[index] /= mean_number;  delta[index] -= 1.0
    #####################################################################

    #####################################################################
    # if there are two or more particles compute auto- and cross-power spectra
    for i,ptype1 in enumerate(particle_type):
        for ptype2 in particle_type[i+1:]:

            # find the indexes of the particle types
            index1 = index_dict[ptype1];  index2 = index_dict[ptype2]

            # choose the name of the output files
            fout1  = 'Pk_' + name_dict[str(ptype1)]             + suffix
            fout2  = 'Pk_' + name_dict[str(ptype2)]             + suffix
            fout12 = 'Pk_' + name_dict[str(ptype1)+str(ptype2)] + suffix

            # some verbose
            print '\nComputing the auto- and cross-power spectra of types: '\
                ,ptype1,'-',ptype2
            print 'saving results in:';  print fout1,'\n',fout2,'\n',fout12

            # This routine computes the auto- and cross-power spectra
            data = PKL.XPk(delta[index1],delta[index2],BoxSize,axis=axis,
                           MAS1='CIC',MAS2='CIC',threads=cpus)
                                                        
            k = data[0];   Nmodes = data[10]

            # save power spectra results in the output files
            np.savetxt(fout12,np.transpose([k,data[1],data[2],data[3],Nmodes]))
            np.savetxt(fout1, np.transpose([k,data[4],data[5],data[6],Nmodes]))
            np.savetxt(fout2, np.transpose([k,data[7],data[8],data[9],Nmodes]))
    #####################################################################

    #####################################################################
    # compute the power spectrum of the sum of all components
    print '\ncomputing P(k) of all components'

    # define delta of all components
    delta_tot = np.zeros((dims,dims,dims),dtype=np.float32)

    Omega_tot = 0.0;  fout = 'Pk_'
    for ptype in particle_type:
        index = index_dict[ptype]
        delta_tot += (Omega_dict[ptype]*delta[index])
        Omega_tot += Omega_dict[ptype]
        fout += name_dict[str(ptype)] + '+'

    delta_tot /= Omega_tot;  del delta;  fout = fout[:-1] #avoid '+' in the end
    
    # compute power spectrum
    [k,Pk0,Pk2,Pk4,Nmodes] = PKL.Pk(delta_tot,BoxSize,axis=axis,MAS='CIC',
                                    threads=cpus);  del delta_tot

    # write P(k) to output file
    np.savetxt(fout+suffix, np.transpose([k,Pk0,Pk2,Pk4,Nmodes]))
###############################################################################
###############################################################################