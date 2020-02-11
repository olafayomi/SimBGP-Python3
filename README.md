# SimBGP
SimBGP is a lightweight event-driven simulator developed by Jian Qiu. This version of SimBGP was developed to provide support to the ADD-Paths BGP extension by Virginie Van den Schrieck at the IP Networking Lab [(INL)](https://inl.info.ucl.ac.be/softwares/simbgp-addpaths-support).

## Changes
* Port the version of SimBGP with ADD-Paths to Python 3
* Fix bugs introduced as a result of porting code to Python 3
* Improve IGP layer by ensuring the cost of links provided in config file is
  passed as a weight attribute when creating link/edges and then used in shortest 
  path calculation between nodes as opposed to using the default weight attribute 
  which is one.
