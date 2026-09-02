pragma solidity ^0.4.18;

contract USDT {
    mapping(address => mapping(address => uint256)) public allowed;
    mapping(address => uint256) public balances;
    uint256 public totalSupply_;
    bool public mintingFinished = false;
    string public constant name = "Tether USD";
    string public constant symbol = "USDT";
    uint8 public constant decimals = 6;
    
    address public owner;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 amount);
    event MintFinished();
    
    modifier onlyOwner() {
        require(msg.sender == owner);
        _;
    }
    
    modifier canMint() {
        require(!mintingFinished);
        _;
    }
    
    function USDT(address _to, uint256 _amount) public {
        owner = msg.sender;
        totalSupply_ = totalSupply_ + _amount;
        balances[_to] = balances[_to] + _amount;
        Transfer(0x0, _to, _amount);  // FIXED: No emit, use 0x0
    }
    
    function totalSupply() public constant returns (uint256) {
        return totalSupply_;
    }
    
    function balanceOf(address _owner) public constant returns (uint256) {
        return balances[_owner];
    }
    
    function transfer(address _to, uint256 _value) public returns (bool) {
        require(_to != 0x0);
        require(_value <= balances[msg.sender]);
        balances[msg.sender] -= _value;
        balances[_to] += _value;
        Transfer(msg.sender, _to, _value);  // FIXED: Direct call
        return true;
    }
    
    function transferFrom(address _from, address _to, uint256 _value) public returns (bool) {
        require(_to != 0x0);
        require(_value <= balances[_from]);
        require(_value <= allowed[_from][msg.sender]);
        balances[_from] -= _value;
        balances[_to] += _value;
        allowed[_from][msg.sender] -= _value;
        Transfer(_from, _to, _value);
        return true;
    }
    
    function approve(address _spender, uint256 _value) public returns (bool) {
        allowed[msg.sender][_spender] = _value;
        Approval(msg.sender, _spender, _value);
        return true;
    }
    
    function allowance(address _owner, address _spender) public constant returns (uint256) {
        return allowed[_owner][_spender];
    }
    
    function mint(address _to, uint256 _amount) public onlyOwner canMint returns (bool) {
        totalSupply_ = totalSupply_ + _amount;
        balances[_to] = balances[_to] + _amount;
        Mint(_to, _amount);
        Transfer(0x0, _to, _amount);  // FIXED
        return true;
    }
    
    function finishMinting() public onlyOwner canMint returns (bool) {
        mintingFinished = true;
        MintFinished();
        return true;
    }
}