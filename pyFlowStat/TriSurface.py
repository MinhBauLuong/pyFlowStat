'''
TriSurface.py

See domcumention in class definition
'''
import re

import numpy as np


class TriSurface(object):
    """
    class TriSurface
    
    A TriSurface object "triSurf" reads and holds a cutting plane "pl" of a 3D field. "pl" must be planar (...) but can be in
    any orientation. To plot "pl" as a contour plot "cplt", the x and y direction of "cplt" must be specified to "triSurf" with
    xViewBasis and yViewBasis. With xViewBasis and yViewBasis, you can entirely control how "triSurf" is displayed.
    
    Note:
        * Sbasis is the standard basis e1=(1,0,0), e1=(0,1,0), e1=(0,0,1). "triSurf" and the 3D fields are defined in this basis
        * Vbasis is the view basis. Vbasis definition in Sbasis is:v1=xViewBasis, v2=yViewBasis, v3=v1 x v2. v1 and v2 must be in the plane.
    
    See also:
        * matplotlib.pyplot.tricontourf: surface plot
        * matplotlib.pyplot.tricontour:  contour plot
        * matplotlib.pyplot.triplot:     plot mesh
        
    """
    
    def __init__(self,storeMesh=True):
        # should the mesh be stored in this object?
        self.storeMesh = storeMesh       
        
        #input path for vars, points and faces
        self.varsFile = str()
        self.pointsFile = str()
        self.facesFile = str()
        
        # vars, point and faces (poits in original basis, not in tilted basis)
        self.vars = None
        self.varRank = int()
        self.points = None   
        self.xys = None
        self.faces = None
        
        # data of the plane in original basis
        self.plDef = None

        # transfomation matrix and vector to display data into the alternate point of view
        self.viewAnchor = None  #view anchor
        self.viewBasis = None   #view basis     
        #self.tranVec = None     #translation vectoc
        #self.rotMat = None      #rotation matrix
        self.affMat = None      #affine transformation (from standard basis to view basis)
        self.invAffMat = None   # inverse of affine transformation matrix      


    def readFromFoamFile(self,varsFile,pointsFile,facesFile,viewAnchor,xViewBasis,yViewBasis):
        '''
        Read planar surface generated by the OpenFOAM sample tool or sampling library.
        
        Notes:
            * This function acts almost like a constructor
            * See notes of function parseFoamFile()
            * Sbasis is the standard basis e1=(1,0,0), e1=(0,1,0), e1=(0,0,1).
            * Vbasis is the view basis. Vbasis definition in Sbasis is:v1=xViewBasis, v2=yViewBasis, v3=v1 x v2. v1 and v2 must be in the plane.
            
        Arguments:
            * varsFile:   [str()] Path of the foamFile with variable
            * pointsFile: [str()] Path of the foamFile with points
            * facesFile:  [str()] Path of the foamFile with faces
            * viewAnchor: [np.array or list(), shape=(3,1)] view anchor in Sbasis. The anchor will become the (0,0) in surface/coutour plot
            * xViewBasis: [np.array or list(), shape=(3,1)] x direction of the view in Sbasis.
            * yViewBasis: [np.array or list(), shape=(3,1)] y direction of the view in Sbasis.

        Modified/updated/initialised members:
            * vars:   [np.array(), vars.shape=(N*3)] list of variables
            * varRank: [int()] rank of the variable stored in vars.
            * points: [np.array(), points.shape=(N*3)] list of points
            * faces:  [np.array(), faces.shape=(N*3)] list of faces
            * xys: [np.array(), xys.shape=(N*2)] list of points in Vbasis. Use those x and y for contour/surface plot!
            * viewAnchor: [np.array, viewAnchors.shape=(3)] anchor on the plane. Use to define the (0,0) for ploting.
            * viewBasis: [np.array, viewBasis.shape=(3x3)] Vbasis defined in Sbasis
            * affMat:    [np.array, affMat.shape=(4x4)] affine transformation matrix for transfomation from Sbasis to Vbasis
            * invAffMat: [np.array, affMat.shape=(4x4)] inverse of affMat
            * plDef: [np.array, plDef.shape=(4)] plane parameters (a,b,c,d). See function TriSurface.genPlaneData() for more infos.
        '''
        # Source of datas
        self.varsFile = varsFile
        self.pointsFile = pointsFile
        self.facesFile = facesFile
        # read variable
        self.vars = parseFoamFile(varsFile)
        self.varRank = len(self.vars[1,:])
        # read mesh if needed and generate tansformation data (mendatory)   
        if self.storeMesh==True:
            self.points = parseFoamFile(pointsFile)
            self.faces = parseFoamFile(facesFile)[:,1:4]
            self.plDef = self.genPlaneData(self.points)
            # generate transformation stuff with points, viewAnchor and view Basis
            self.viewAnchor  = viewAnchor
            self.affMat,self.invAffMat,self.viewBasis = self.genTransData(self.points,self.viewAnchor,xViewBasis,yViewBasis)           
            # generate planar coordinate X and Y
            self.xys = np.zeros((self.points.shape[0],2))
            for i in range(self.xys.shape[0]):
                ptInA = self.points[i,:]
                ptInB = np.dot(self.affMat , self.affineVec(ptInA).reshape((4,1)))[0:3]
                ptInB = np.dot(self.affMat , self.affineVec(ptInA))[0:3]
                self.xys[i,:] = ptInB[0:2]
        else:
            points = parseFoamFile(pointsFile)
            self.plDef = self.genPlaneData(points)
            # generate transformation stuff with points, viewAnchor and view Basis   
            self.viewAnchor  = viewAnchor
            self.affMat,self.invAffMat,self.viewBasis = self.genTransData(points,self.viewAnchor,xViewBasis,yViewBasis)
                
                
    def constructFromArray(self,varsArray,pointsArray,facesArray,viewAnchor,xViewBasis,yViewBasis):
        '''
        Construct surface by passing numpy array for vars, points and faces.
        
        Notes:
            * This function acts almost like a constructor
            * Sbasis is the standard basis e1=(1,0,0), e1=(0,1,0), e1=(0,0,1).
            * Vbasis is the view basis. Vbasis defined in Sbasis is:v1=xViewBasis, v2=yViewBasis, v3=v1 x v2. v1 and v2 must be in the plane.
            
        Arguments:
            * varsFile:   [str()] list of variables
            * pointsFile: [str()] list of pointsassociated with 
            * facesFile:  [str()] Path of the foamFile with faces
            * viewAnchor: [np.array or list(), shape=(3,1)] view anchor in Sbasis. The anchor will become the (0,0) in surface/coutour plot
            * xViewBasis: [np.array or list(), shape=(3,1)] x direction of the view in Sbasis.
            * yViewBasis: [np.array or list(), shape=(3,1)] y direction of the view in Sbasis.

        Modified/updated/initialised members:
            * vars:   [np.array(), vars.shape=(N*3)] list of variables
            * varRank: [int()] rank of the variable stored in vars.
            * points: [np.array(), points.shape=(N*3)] list of points
            * faces:  [np.array(), faces.shape=(N*3)] list of faces
            * xys: [np.array(), xys.shape=(N*2)] list of points in Vbasis. Use those x and y for contour/surface plot!
            * viewAnchor: [np.array, viewAnchors.shape=(3)] anchor on the plane. Use to define the (0,0) for ploting.
            * viewBasis: [np.array, viewBasis.shape=(3x3)] Vbasis defined in Sbasis
            * affMat:    [np.array, affMat.shape=(4x4)] affine transformation matrix for transfomation from Sbasis to Vbasis
            * invAffMat: [np.array, affMat.shape=(4x4)] inverse of affMat
            * plDef: [np.array, plDef.shape=(4)] plane parameters (a,b,c,d). See function TriSurface.genPlaneData() for more infos.
        '''
        # check array length
        if len(varsArray)!=len(pointsArray):
            print('varsArray and pointsArray must have the same dimension. Exit')
            exit
        # Source of datas
        self.varsFile = ''
        self.pointsFile = ''
        self.facesFile = ''
        # read variable
        self.vars = np.copy(varsArray)
        self.varRank = len(self.vars[1,:])
        # read mesh if needed and generate tansformation data (mendatory)
        if self.storeMesh==True:
            self.points = np.copy(pointsArray)
            self.faces = np.copy(facesArray)
            self.plDef = self.genPlaneData(self.points)
            # generate transformation stuff with points, viewAnchor and view Basis
            self.viewAnchor  = viewAnchor
            self.affMat,self.invAffMat,self.viewBasis = self.genTransData(self.points,self.viewAnchor,xViewBasis,yViewBasis)           
            # generate planar coordinate X and Y
            self.xys = np.zeros((self.points.shape[0],2))
            for i in range(self.xys.shape[0]):
                ptInA = self.points[i,:]
                ptInB = np.dot(self.affMat , self.affineVec(ptInA).reshape((4,1)))[0:3]
                ptInB = np.dot(self.affMat , self.affineVec(ptInA))[0:3]
                self.xys[i,:] = ptInB[0:2]
        else:
            points = np.copy(pointsArray)
            self.plDef = self.genPlaneData(points)
            # generate transformation stuff with points, viewAnchor and view Basis   
            self.viewAnchor  = viewAnchor
            self.affMat,self.invAffMat,self.viewBasis = self.genTransData(points,self.viewAnchor,xViewBasis,yViewBasis)
        

    
    def readFromVTK(self,vtkFile,viewAnchor,xViewBasis,yViewBasis):
        '''
        Read a VTK planar surface generated by the OpenFOAM sample tool or sampling library.
        
        /!\ Not impemented /!\
        /!\ Not impemented /!\
        /!\ Not impemented /!\
        
        Notes:
            * This function acts almost like a constructor
            * vtk module for python must be available
            * Sbasis is the standard basis e1=(1,0,0), e1=(0,1,0), e1=(0,0,1).
            * Vbasis is the view basis. Vbasis definition in Sbasis is:v1=xViewBasis, v2=yViewBasis, v3=v1 x v2. v1 and v2 must be in the plane.
            
        Arguments:
            * varsFile:   [str()] Path of the foamFile with variable
            * pointsFile: [str()] Path of the foamFile with points
            * facesFile:  [str()] Path of the foamFile with faces
            * viewAnchor: [np.array or list(), shape=(3,1)] view anchor in Sbasis. The anchor will become the (0,0) in surface/coutour plot
            * xViewBasis: [np.array or list(), shape=(3,1)] x direction of the view in Sbasis.
            * yViewBasis: [np.array or list(), shape=(3,1)] y direction of the view in Sbasis.

        Modified/updated/initialised members:
            * vars:   [np.array(), vars.shape=(N*3)] list of variables
            * varRank: [int()] rank of the variable stored in vars.
            * points: [np.array(), points.shape=(N*3)] list of points
            * faces:  [np.array(), faces.shape=(N*3)] list of faces
            * xys: [np.array(), xys.shape=(N*2)] list of points in Vbasis. Use those x and y for contour/surface plot!
            * viewAnchor: [np.array, viewAnchors.shape=(3)] anchor on the plane. Use to define the (0,0) for ploting.
            * viewBasis: [np.array, viewBasis.shape=(3x3)] Vbasis defined in Sbasis
            * affMat:    [np.array, affMat.shape=(4x4)] affine transformation matrix for transfomation from Sbasis to Vbasis
            * invAffMat: [np.array, affMat.shape=(4x4)] inverse of affMat
            * plDef: [np.array, plDef.shape=(4)] plane parameters (a,b,c,d). See function TriSurface.genPlaneData() for more infos.
        '''
        pass

       
    def genPlaneData(self,points):
        '''
        Generate parameters (a,b,c,d) of plane equation ax+by+cz+d=0. The plane is defined
        with the list of points "points".
        
        Arguments:
            * points: [np.array, points.shape=(N,3)] list of N 3D points (in Sbasis).
        
        Returns:
            * plDef: [np.array, plDef.shape=(4)] parameters (a,b,c,d).
        ''' 
        # get the plane normal from list of points define with basis orig
        v1 = points[1,:]-points[0,:]
        v2 = points[2,:]-points[0,:]
        plNorm = np.cross(v1,v2)
        
        # get vector which define the plane in space
        plDef = np.zeros(4)
        plDef[0:3] = plDef[0:3]+plNorm
        afpt = self.affineVec(points[0,:])
        c = np.dot(plDef,afpt)
        plDef[3] = -c
        return plDef

        
    def genTransData(self,points,viewAnchor,xViewBasis,yViewBasis):
        '''
        Generate affine transformation matrix T and its inverse invT. viewBasis is also returned.
        
        Notes:
            * For a given position P defined in Sbasis (PinS), the same position (physical meaning) defined
              in Vbasis can be computed like:
                  * T*PinS = PinV
                  *invT*PinV = PinS
        
        Arguments:
            * points: [np.array, points.shape=(N,3)] list of N 3D points (in Sbasis).
            * viewAnchor: [np.array, viewAnchors.shape=(3)] anchor on the plane. Use to define the (0,0) for ploting.
            * xViewBasis: [np.array, xViewBasis.shape=(3)] first basis vector of Vbasis. Defined in Sbasis.
            * yViewBasis: [np.array, yViewBasis.shape=(3)] second basis vector of Vbasis. Defined in Sbasis.
        
        Returns:
            * T: [np.array, T.shape=(4x4)] affine transformation matrix from Sbasis to Vbasis.
            * invT: [np.array, invT.shape=(4x4)] inverse of T.
            * viewBasis: [np.array, viewBasis.shape=(3x3)] Vbasis defined in Sbasis
        '''         
        viewBasis = np.zeros((3,3))
        zViewBasis = np.cross(xViewBasis,yViewBasis)
        viewBasis[:,0] = xViewBasis        
        viewBasis[:,1] = yViewBasis
        viewBasis[:,2] = zViewBasis
        
        # get affine matrix of the transformation
        #   A is the orignal basis of the plane, namely: the standard basis (A =np.identity(3))
        #   B is the view basis. x and y are the in plane, z is the normal. z also define the view direction
        #   for a given vecto V:
        #       VinB stands for V decribes with basis B
        #       VinA stands for V decribes with basis A  

        # T = affine tranformation matrix from A->B.
        #   T*VinA = VinB
        #   invT*VinB = VinA
        translation = viewAnchor-np.zeros(3)
        invT = self.affineMat(viewBasis,translation)
        T = np.linalg.inv(invT)

        return T,invT,viewBasis


    def affineVec(self,vec):
        '''
        Return affine vector from standard vector
        
        Arguments:
            * vec: [np.array. trans.shape=(3)] a vector
        
        Return:
            * affineVec [np.array. affineMat.shape=(4)] the affine Vector. Same as vec, but with a trailing 1.
        '''
        affineVec = np.zeros(len(vec)+1)
        affineVec[-1] = 1
        affineVec[0:len(vec)] = affineVec[0:len(vec)]+vec
        return affineVec

    
    def affineMat(self,mat,trans):
        '''
        Return affine matrix from standard matrix.
        
        Arguments:
            * mat: [np.array. mat.shape=(3,3)] a matrix.
            * trans: [np.array. trans.shape=(3)] translation vector from Sbasis to Vbasis, express in Sbasis.
        
        Return:
            * affineMat [np.array. affineMat.shape=(4,4)] the affine Matrix.
        '''
        nbl = mat.shape[0]  #number of line
        nbr = mat.shape[0]  #number of row
        affineMat = np.zeros((nbl+1,nbr+1))
        affineMat[0:nbl,0:nbl] = affineMat[0:nbl,0:nbl]+mat
        affineMat[0:nbr,-1] = affineMat[0:nbr,-1] + trans
        affineMat[-1,-1] = 1
        return affineMat

        
    def isColinear(self,vec1,vec2):
        '''
        return true if vec1 and vec2 are colinear
        '''
        if np.cross(vec1,vec2)==np.zeros(len(vec1)):
            return True
        else:
            return False

### END class TriSurface()        
        
def parseFoamFile(foamFile):
    '''
    Parse a foamFile generated by the OpenFOAM sample tool or sampling library.
    
    Note:
        * It's a primitiv parse, do not add header in your foamFile!
        * Inline comment are allowed only from line start. c++ comment style.
        
    Arguments:
        * foamFile: [str()] Path of the foamFile

    Returns:
        * output: [numpy.array()] data store in foamFile
    '''
    output = []
    catchFirstNb = False
    istream = open(foamFile, 'r')
    for line in istream: 
        # This regex finds all numbers in a given string.
        # It can find floats and integers writen in normal mode (10000) or with power of 10 (10e3).
        match = re.findall('[-+]?\d*\.?\d+e*[-+]?\d*', line)
        if (line.startswith('//')):
            pass
        if (catchFirstNb==False and len(match)==1):
            catchFirstNb = True
        elif (catchFirstNb==True and len(match)>0):
            matchfloat = list()
            for nb in match:                
                matchfloat.append(float(nb))
            output.append(matchfloat)
        else:
            pass
    istream.close()
    return np.array(output)        

        
def parseVTK(vtkFile):
    '''
    Parse VTK file of a plane in space. vtk generate by the OpenFOAM sample tool.
    /!\ Not impemented /!\ 
    '''
    pass      
        

def getVar(self,point,interpolation='linear',pointBasis='default',points=None,faces=None,):
    '''
    Return "var" at location "point" according "interpolation". "interpolation" can be one of
    the following:
        * nearest
        * linear (default)
        * cubic
    
    /!\ Not impemented /!\ 
    '''
    pass       