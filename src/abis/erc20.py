ERC20_ABI = [
    {
       "constant": True,
       "inputs": [],
       "name": "decimals",
       "outputs": [
           {
               "name": "",
               "type": "uint256"
           }
       ],
       "payable": False,
       "stateMutability": "view",
       "type": "function"
    },
    {
       "constant": True,
       "inputs": [
           {
               "name": "who",
               "type": "address"
           }
       ],
       "name": "balanceOf",
       "outputs": [
           {
               "name": "",
               "type": "uint256"
           }
       ],
       "payable": False,
       "stateMutability": "view",
       "type": "function"
    },
    {
       "constant": False,
       "inputs": [
           {
               "name": "_to",
               "type": "address"
           },
           {
               "name": "_value",
               "type": "uint256"
           }
       ],
       "name": "transfer",
       "outputs": [],
       "payable": False,
       "stateMutability": "nonpayable",
       "type": "function"
    }
]
