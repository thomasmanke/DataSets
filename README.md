## DataSets

This is a personal collection of data sets for easy programmatic access
with github URLs.

The main purpose is to provide access to selected datasets as part of courses on Data Science and Statistics.

All original works, authors, collectors and resources gratefully acknowledged and summarized below:

| File           | Origin | Authors |  Date  | License |
|:---------------|:---------|:--------|:-------|:-------   |
| volano_events_noaa.tsv |  NOAA [^1] | N. Arcos | 2024.08.09 | unrestricted |
| earthquake_events_noaa.tsv |  NOAA [^2] | N. Arcos | 2024.08.09 | unrestricted |
| MNIST | Yann LeCun [^3] | Yann LeCun, Corinna Cortes, Christopher J.C. Burges | 1998 | unrestricted |
| iris.csv.gz | R Core Team [^4] | Ronald A. Fisher | 1936 | unrestricted |
| Berlin.geojson | OSM [^5] | OpenStreetMap | 2025 | unrestricted |

## checksums
shasum -a 256 *gz > checksum.txt

## References

[^1]:  National Geophysical Data Center / World Data Service (NGDC/WDS): NCEI/WDS Global Significant Volcanic Eruptions Database. NOAA National Centers for Environmental Information. doi:10.7289/V5JW8BSH [2024/08/09]. 
https://www.ngdc.noaa.gov/hazel/view/hazards/volcano/event-data .

[^2]:  National Geophysical Data Center / World Data Service (NGDC/WDS): NCEI/WDS Global Significant Earthquake Database. NOAA National Centers for Environmental Information. doi:10.7289/V5TD9V7K [2024/08/09]. 
https://www.ngdc.noaa.gov/hazel/view/hazards/earthquake/event-data

[^3]: LeCun, Yann and Bottou, L{\'e}on and Bengio, Yoshua and Haffner, Patrick. Gradient-based learning applied to document recognition, Proceedings of the IEEE 86(11):2278-2324, 1998. Data available at https://huggingface.co/datasets/ylecun/mnist and https://www.kaggle.com/datasets/oddrationale/mnist-in-csv.

[^4]: Fisher, R.A. "The use of multiple measurements in taxonomic problems." Annals of Eugenics, 7, Part II, 179-188 (1936); also in "Contributions to Mathematical Statistics" (John Wiley, NY, 1950). Data available with from base R.

[^5]: curl "http://polygons.openstreetmap.fr/get_geojson.py?id=62422" > Berlin.geojson
   micromamba create env -n maps -f envs/maps_env.yml
   micromamba activate maps
   python scripts/geojson2raster.py --input Berlin.geojson --out-prefix Berlin_50x50 --width 50 --height 50 --format png

