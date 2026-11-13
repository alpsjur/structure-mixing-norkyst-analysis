#!/bin/bash -f
#$ -N current
#$ -cwd -b n
#$ -l h_rt=04:00:00
#$ -l h_rss=16G,mem_free=16G,h_data=16G
#$ -S /bin/bash
#$ -q bigmem-r8.q
#$ -M ansju8054@met.no
#$ -m ae
#$ -j y
#$ -o /lustre/storeB/users/ansju8054/logs/

source /modules/rhel9/x86_64/mamba-mf3/etc/profile.d/ppimam.sh
mamba activate structure-mixing-norkyst-analysis


# Loop over months from 02 to 08
for month in {02..08}; do
    echo "Processing month: 2022-$month"

    # Mean calculations
    echo "  Mean"
    python3 scripts/computations/make_monthly_mean.py wakeref 2022-$month

    # Anomalies calculations
    echo "  Anomalies"
    python3 scripts/computations/make_monthly_anomalies.py spar 2022-$month
    python3 scripts/computations/make_monthly_anomalies.py semisub 2022-$month

    # Currents calculations
    echo "  Currents"
    python3 scripts/computations/make_current.py spar 2022-$month
    python3 scripts/computations/make_current.py semisub 2022-$month
    python3 scripts/computations/make_current.py wakeref 2022-$month

    # PEA calculations for default range
    echo "  PEA (default range)"
    python3 scripts/computations/make_pea.py spar 2022-$month
    python3 scripts/computations/make_pea.py semisub 2022-$month
    python3 scripts/computations/make_pea.py wakeref 2022-$month

    # PEA calculations for specific zmax ranges
    for zmin in -50 -100 -150; do
        echo "  PEA (zmin=$zmin, zmax=0)"
        zmin_abs=${zmin#-}
        output_dir="/lustre/storeB/project/nwp/havvind/structure_mixing/processed/pea${zmin_abs}"
        python3 scripts/computations/make_pea.py spar 2022-$month --zmin $zmin --zmax 0 --outdir $output_dir
        python3 scripts/computations/make_pea.py semisub 2022-$month --zmin $zmin --zmax 0 --outdir $output_dir
        python3 scripts/computations/make_pea.py wakeref 2022-$month --zmin $zmin --zmax 0 --outdir $output_dir
    done
done
