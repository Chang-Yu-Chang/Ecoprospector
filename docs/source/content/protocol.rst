Selection Protocol
==================

What is a selection protocol?
---------------------------------------------------

A selection protocol is a table that defines the selected function, selection regime, and the number of community generations.

How does a selection protocol in ecoprospector look like? Inspired by batch culture experiments of microbial communities, we specify the selection protocol in a transfer/generation-wise manner. Here is an example of no-selection (simple_screening) protocol where it is simply doing nothing but passaging the plate in every transfer :

[insert an example protocol table of no-selection protocol ]

A selection protocol is then a table with four columns: 

* Protocol name: specified by ``protocol`` in the input ``csv``.
* Transfer or community generation.
* :ref:`Community Function`: the community function under selection at each transfer.
* :ref:`Selection Matrix`: the selection regime conducted at each transfer. 


How to make a selection protocol
--------------------------------

The selection protocol is automatically generated by ecoprospector with the mapping ``csv``. Key parameters include the specified protocol (``protocol``) the number of total transfers (``n_transfer``) and the number of selection transfers (``n_transfer_selection``).

By default, ecoprospector will divide the protocol into two phases: selection and stabilization. In each transfer of the selection phase, a subset of the metacommunity is selected and used to seed the next generation. The selection matrix is consecutively implemented for ``n_transfer_selection`` times. Then for the rest of transfers until ``n_transfer``, the metacommunity is stabilized by simply passaged without selection. 

There are some examples of default selection protocols, which are contained in the ``E_protocols.py``.

Note that users can make their  own protocol without regard to the ecoprospector predefined protocols. To do that, make a pandas DataFrame with the same column names and include it in the ``E_protocols.py``, and make sure that:

* The number of transfers does not exceed the ``n_transfer``
* The selection matrix specified in the protocol is contained in ``C_selection_matrices.py``
* Specify the new protocol name in the input ``csv``.

What a selection protocol does not do
---------------------------------------------------

While the table form of a selection protocol is a convenient way to standardize empirical protocols, some features that are usually specified in a “protocol” at an experimental setting are  not included:

* The number of communities (``n_wells``) in a metacommunity.
* Dilution factor (``l``)
* Incubation time (``n_propagation``)
* Media or resource composition

Instead these parameters, either specified in the mapping ``csv`` or generated during simulation setup, become object attributes of the :ref:`Metacommunity` during simulation.

