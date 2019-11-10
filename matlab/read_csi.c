/*
 * =====================================================================================
 *       Filename:  read_csi.c
 *
 *    Description:  read csi for matlab 
 *        Version:  1.0
 *
 *         Author:  Yaxiong Xie
 *         Email :  <xieyaxiongfly@gmail.com>
 *   Organization:  WNADS group @ Nanyang Technological University
 *
 *   Copyright (c)  WANDS group @ Nanyang Technological University
 * =====================================================================================
 */
#include "mex.h"

#define TONE_40M 114
#define BITS_PER_BYTE 8
#define BITS_PER_SYMBOL      10
#define BITS_PER_COMPLEX_SYMBOL (2 * BITS_PER_SYMBOL)

typedef struct
{
    int real;
    int imag;
}COMPLEX;

int signbit_convert(int data, int maxbit)
{
    if (data & (1 << (maxbit - 1))) 
    { /*  negative */
        data -= (1 << maxbit);
    }
    return data;
}
void mexFunction(int nlhs, mxArray *plhs[],
            int nrhs, const mxArray *prhs[])
{
    unsigned char *local_h;
    unsigned int  *csi_len_p,csi_len;
    unsigned int  *nr_p,nr;
    unsigned int  *nc_p,nc;
    unsigned int  *h_size_p, h_size;
    unsigned int  *num_tones_p,num_tones;

    unsigned int  bitmask, idx, current_data;
    unsigned int  h_data;
    

    int  k;
    int  real, imag;
    int  bits_left, nc_idx, nr_idx;
    
    /*  check for proper number of arguments */
    if(nrhs!=5) {
        mexErrMsgIdAndTxt("MIMOToolbox:read_csi_new:nrhs","Four input required.");
    }
    if(nlhs!=1) {
        mexErrMsgIdAndTxt("MIMOToolbox:read_csi_new:nlhs","One output required.");
    }
    /*  make sure the input argument is a char array */
    if (!mxIsClass(prhs[0], "uint8")) {
        mexErrMsgIdAndTxt("MIMOToolbox:read_csi_new:notBytes","Input must be a char array");
    }
  
    local_h = mxGetData(prhs[0]);

    h_size_p  = (unsigned int *) mxGetPr(prhs[1]);
    h_size    = *h_size_p;

    nr_p  = (unsigned int *) mxGetPr(prhs[2]);
    nr    = *nr_p;

    nc_p  = (unsigned int *) mxGetPr(prhs[3]);
    nc    = *nc_p;

    num_tones_p = (unsigned int *) mxGetPr(prhs[4]);
    num_tones   = *num_tones_p;

    mwSize size[]  = {nr, nc, num_tones};

    mxArray *csi  = mxCreateNumericArray(3, size, mxDOUBLE_CLASS, mxCOMPLEX);
    double * ptrR =(double *)mxGetPr(csi);
    double * ptrI =(double *)mxGetPi(csi);
    
    bits_left = 16; /* process 16 bits at a time */

    /* 10 bit resoluation for H real and imag */
    bitmask = (1 << BITS_PER_SYMBOL) - 1;
    idx = 0;
    h_data = local_h[idx++];
    h_data += (local_h[idx++] << BITS_PER_BYTE);
    current_data = h_data & ((1 << 16) - 1); /* get 16 LSBs first */
    
    for (k = 0; k < num_tones; k++) {
        for (nc_idx = 0; nc_idx < nc; nc_idx++) {
            for (nr_idx = 0; nr_idx < nr; nr_idx++) {
                if ((bits_left - BITS_PER_SYMBOL) < 0) {
                    /* get the next 16 bits */
                    h_data = local_h[idx++];
                    h_data += (local_h[idx++] << BITS_PER_BYTE);
                    current_data += h_data << bits_left;
                    bits_left += 16;
                }
                imag = current_data & bitmask;
                
                imag = signbit_convert(imag, BITS_PER_SYMBOL);
		        *ptrI = (double) imag;
		        ++ptrI;
                bits_left -= BITS_PER_SYMBOL;
                /* shift out used bits */
                current_data = current_data >> BITS_PER_SYMBOL; 

                if ((bits_left - BITS_PER_SYMBOL) < 0) {
                    /* get the next 16 bits */
                    h_data = local_h[idx++];
                    if (h_size != idx) {
                        h_data += (local_h[idx++] << BITS_PER_BYTE);
                        current_data += h_data << bits_left;
                        bits_left += 16;
                    } else {
                        current_data += h_data << bits_left;
                        bits_left += 8;
                    }
                }
                real = current_data & bitmask;
                
                real = signbit_convert(real, BITS_PER_SYMBOL);
		        *ptrR = (double) real;
		        ++ptrR;
                bits_left -= BITS_PER_SYMBOL;
                
                /* shift out used bits */
                current_data = current_data >> BITS_PER_SYMBOL;
                
            }
        }
    }
    plhs[0] = csi;
}

