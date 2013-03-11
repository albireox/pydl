# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-
def djs_reject(data,model,outmask=None,inmask=None,sigma=None,invvar=None,
    lower=None,upper=None,maxdev=None,
    maxrej=None,groupdim=None,groupsize=None,groupbadpix=False,
    grow=0,sticky=False):
    """Routine to reject points when doing an iterative fit to data.

    Parameters
    ----------
    data : ndarray
        The data
    model : ndarray
        The model, must have the same number of dimensions as `data`.
    outmask : ndarray, optional
        Output mask, generated by a previous call to `djs_reject`.  If not supplied,
        this mask will be initialized to a mask that masks nothing.  Although
        this parameter is technically optional, it will almost always be set.
    inmask : ndarray, optional
        Input mask.  Bad points are marked with a value that evaluates to ``False``.
        Must have the same number of dimensions as `data`.
    sigma : ndarray, optional
        Standard deviation of the data, used to reject points based on the values
        of `upper` and `lower`.
    invvar : ndarray, optional
        Inverse variance of the data, used to reject points based on the values
        of `upper` and `lower`.  If both `sigma` and `invvar` are set, `invvar`
        will be ignored.
    lower : int or float, optional
        If set, reject points with data < model - lower * sigma.
    upper : int or float, optional
        If set, reject points with data > model + upper * sigma.
    maxdev : int or float, optional
        If set, reject points with abs(data-model) > maxdev.  It is permitted to
        set all three of `lower`, `upper` and `maxdev`.
    maxrej : int or ndarray, optional
        Maximum number of points to reject in this iteration.  If `groupsize` or
        `groupdim` are set to arrays, this should be an array as well.
    groupdim
    groupsize
    groupbadpix : bool, optional
        If set to ``True``, consecutive sets of bad pixels are considered groups,
        overriding the values of `groupsize`.
    grow : int, optional
        If set to a non-zero integer, N, the N nearest neighbors of rejected
        pixels will also be rejected.
    sticky : bool, optional
        If set to ``True``, pixels rejected in one iteration remain rejected in
        subsequent iterations, even if the model changes.

    Returns
    -------
    djs_reject : tuple
        A tuple containing a mask where rejected data values are ``False`` and
        a boolean value set to ``True`` if `djs_reject` believes there is no
        further rejection to be done.

    Raises
    ------
    ValueError
        If dimensions of various inputs do not match.
    """
    import numpy as np
    from ..misc import djs_laxisnum
    #
    # Create outmask setting = 1 for good data.
    #
    if outmask is None:
        outmask = np.ones(data.shape,dtype='bool')
    else:
        if data.shape != outmask.shape:
            raise ValueError('Dimensions of data and outmask do not agree.')
    #
    # Check other inputs.
    #
    if model is None:
        if inmask is not None:
            outmask = inmask
        return (outmask,False)
    else:
        if data.shape != model.shape:
            raise ValueError('Dimensions of data and model do not agree.')
    if inmask is not None:
        if data.shape != inmask.shape:
            raise ValueError('Dimensions of data and inmask do not agree.')
    if maxrej is not None:
        if groupdim is not None:
            if len(maxrej) != len(groupdim):
                raise ValueError('maxrej and groupdim must have the same number of elements.')
        else:
            groupdim = []
        if groupsize is not None:
            if len(maxrej) != len(groupsize):
                raise ValueError('maxrej and groupsize must have the same number of elements.')
        else:
            groupsize = len(data)
    if sigma is None and invvar is None:
        if inmask is not None:
            igood = (inmask & outmask).nonzero()[0]
        else:
            igood = outmask.nonzero()[0]
        if len(igood > 1):
            sigma = np.std(data[igood] - model[igood])
        else:
            sigma = 0
    diff = data - model
    #
    # The working array is badness, which is set to zero for good points
    # (or points already rejected), and positive values for bad points.
    # The values determine just how bad a point is, either corresponding
    # to the number of sigma above or below the fit, or to the number
    # of multiples of maxdev away from the fit.
    #
    badness = np.zeros(outmask.shape,dtype=data.dtype)
    #
    # Decide how bad a point is according to lower.
    #
    if lower is not None:
        if sigma is not None:
            qbad = diff < (-lower * sigma)
            badness += ((-diff/(sigma + (sigma == 0))) > 0) * qbad
        else:
            qbad = (diff * np.sqrt(invvar)) < -lower
            badness += ((-diff * np.sqrt(invvar)) > 0) * qbad
    #
    # Decide how bad a point is according to upper.
    #
    if upper is not None:
        if sigma is not None:
            qbad = diff > (upper * sigma)
            badness += ((diff/(sigma + (sigma == 0))) > 0) * qbad
        else:
            qbad = (diff * np.sqrt(invvar)) > upper
            badness += ((diff * np.sqrt(invvar)) > 0) * qbad
    #
    # Decide how bad a point is according to maxdev.
    #
    if maxdev is not None:
        qbad = np.absolute(diff) > maxdev
        badness += np.absolute(diff) / maxdev * qbad
    #
    # Do not consider rejecting points that are already rejected by inmask.
    # Do not consider rejecting points that are already rejected by outmask,
    # if sticky is set.
    #
    if inmask is not None:
        badness *= inmask
    if sticky:
        badness *= outmask
    #
    # Reject a maximum of maxrej (additional) points in all the data, or
    # in each group as specified by groupsize, and optionally along each
    # dimension specified by groupdim.
    #
    if maxrej is not None:
        #
        # Loop over each dimension of groupdim or loop once if not set.
        #
        for iloop in range(max(len(groupdim),1)):
            #
            # Assign an index number in this dimension to each data point.
            #
            if len(groupdim) > 0:
                yndim = len(ydata.shape)
                if groupdim[iloop] > yndim:
                    raise ValueError('groupdim is larger than the number of dimensions for ydata.')
                dimnum = djs_laxisnum(ydata.shape,iaxis=groupdim[iloop]-1)
            else:
                dimnum = 0
            #
            # Loop over each vector specified by groupdim. For example, if
            # this is a 2-D array with groupdim=1, then loop over each
            # column of the data.  If groupdim=2, then loop over each row.
            # If groupdim is not set, then use the whole image.
            #
            for ivec in range(max(dimnum)):
                #
                # At this point it is not possible that dimnum is not set.
                #
                indx = (dimnum == ivec).nonzero()[0]
                #
                # Within this group of points, break it down into groups
                # of points specified by groupsize, if set.
                #
                nin = len(indx)
                if groupbadpix:
                    goodtemp = badness == 0
                    groups_lower = (-1*np.diff(np.insert(goodtemp,0,1)) == 1).nonzero()[0]
                    groups_upper = (np.diff(np.append(goodtemp,1)) == 1).nonzero()[0]
                    ngroups = len(groups_lower)
                else:
                    #
                    # The IDL version of this test makes no sense because
                    # groupsize will always be set.
                    #
                    if 'groupsize' in kwargs:
                        ngroups = nin/groupsize + 1
                        groups_lower = np.arange(ngroups,dtype='i4')*groupsize
                        foo = (np.arange(ngroups,dtype='i4')+1)*groupsize
                        groups_upper = np.where(foo < nin,foo,nin) -1
                    else:
                        ngroups = 1
                        groups_lower = [0,]
                        groups_upper = [nin - 1,]
                for igroup in range(ngroups):
                    i1 = groups_lower[igroup]
                    i2 = groups_upper[igroup]
                    nii = i2 - i1 + 1
                    #
                    # Need the test that i1 != -1 below to prevent a crash
                    # condition, but why is it that we ever get groups
                    # without any points?  Because this is badly-written,
                    # that's why.
                    #
                    if nii > 0 and i1 != -1:
                        jj = indx[i1:i2+1]
                        #
                        # Test if too many points rejected in this group.
                        #
                        if np.sum(badness[jj] != 0) > maxrej[iloop]:
                            isort = badness[jj].argsort()
                            #
                            # Make the following points good again.
                            #
                            badness[jj[isort[0:nii-maxrej[iloop]]]] = 0
                        i1 += groupsize[iloop]
    #
    # Now modify outmask, rejecting points specified by inmask=0, outmask=0
    # if sticky is set, or badness > 0.
    #
    # print badness
    newmask = badness == 0
    # print newmask
    if grow > 0:
        rejects = newmask==0
        if rejects.any():
            irejects = rejects.nonzero()[0]
            for k in range(1,grow):
                newmask[(irejects - k) > 0] = 0
                newmask[(irejects + k) < (data.shape[0]-1)] = 0
    if inmask is not None:
        newmask = newmask & inmask
    if sticky:
        newmask = newmask & outmask
    #
    # Set qdone if the input outmask is identical to the output outmask.
    #
    qdone = np.all(newmask == outmask)
    outmask = newmask
    return (outmask,qdone)

