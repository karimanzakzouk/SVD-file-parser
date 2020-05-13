import xmltodict
import sys
import os
import copy
import re


#read inputs and length of inputs
argv = sys.argv
argc = len(argv)

#check if user pass required inputs or not 
if argc != 3:
   print('ERROR: pass svd file  then required peripheral.......')
   exit(-1)

svd_file = argv[1]
user_peripheral = argv[2]

#read svd file 
svd_file = open(svd_file,'r')
svd_file_data = svd_file.read()
svd_file.close()

#parse svd file data to xmltodict
svd_file = xmltodict.parse(svd_file_data)


#create dictionary of all peripherals
peripherals = {}

#for each peripheral
for peripheral in svd_file['device']['peripherals']['peripheral']:
   #if it has only 1 peripheral
   if not isinstance(peripheral, dict):
      peripheral = svd_file['device']['peripherals']['peripheral']

   peripheral_name = peripheral['name']

   #each peripheral name is a dict
   peripherals[peripheral_name] = {}
   peripherals[peripheral_name]['base'] = peripheral['baseAddress']

   #each peripheral has an IRQ dict
   peripherals[peripheral_name]['irq']  = {}

   #each peripheral has a reg dict
   peripherals[peripheral_name]['reg']  = {}


   #if it's a derived peripheral 
   if '@derivedFrom' in peripheral:
   
      #deep copy the deriving module
      peripherals[peripheral_name] = copy.deepcopy(peripherals[peripheral['@derivedFrom']])

      peripherals[peripheral_name]['base'] = peripheral['baseAddress']
      
      for register_name in peripherals[peripheral_name]['reg']:
         peripherals[peripheral_name]['reg'][register_name]['field'] = {}
         

   #if it's a deriving peripheral
   else:
      peripherals[peripheral_name]['desc']  = peripheral['description']
      peripherals[peripheral_name]['group'] = peripheral['groupName']

      #for each reg in the peripheral
      for reg in peripheral['registers']['register']:
         # if it has only 1 reg
         if not isinstance(reg, dict):
            reg = peripheral['registers']['register']

         register_name = reg['name']

         #each register name is a dict
         peripherals[peripheral_name]['reg'][register_name] = {}

         #each register has a bitfield dict
         peripherals[peripheral_name]['reg'][register_name]['field'] = {}

         peripherals[peripheral_name]['reg'][register_name]['desc']     = re.sub(r'\s+|, ', ' ', reg['description'].strip())
         peripherals[peripheral_name]['reg'][register_name]['offset']   = reg['addressOffset']
         peripherals[peripheral_name]['reg'][register_name]['resetVal'] = reg['resetValue']

         #for each bitfield in the register
         for field in reg['fields']['field']:
            # if it has only 1 bitfield
            if not isinstance(field, dict):
               field = reg['fields']['field']

            field_name = field['name']

            # each bitfield name in the register is a dict
            peripherals[peripheral_name]['reg'][register_name]['field'][field_name] = {}

            peripherals[peripheral_name]['reg'][register_name]['field'][field_name]['desc']   = re.sub(r'\s+|, ', ' ', field['description'].strip())
            peripherals[peripheral_name]['reg'][register_name]['field'][field_name]['offset'] = field['bitOffset']
            peripherals[peripheral_name]['reg'][register_name]['field'][field_name]['width']  = field['bitWidth']



if not user_peripheral in peripherals:
  print('ERROR: peripheral "%s" doesn\'t exist' %(user_peripheral))
  print('peripherals:  ')
  
  for peripheral_name in peripherals:
    print(peripheral_name)
  exit(-1)

C_file = open('%s.c' %(user_peripheral), 'a')

if os.path.getsize(C_file.name) == 0:
  C_file.write("\n/* base address of the module \"%s\" */\n" %(user_peripheral))
  C_file.write("#define  %s_BASE_ADDRESS        (%s)\n" %(user_peripheral, peripherals[user_peripheral]['base']))

  for register_name in peripherals[user_peripheral]['reg']:
     reg = peripherals[user_peripheral]['reg'][register_name]

     C_file.write("\n/* base address and masks for register: %s.%s (%s), reset value = %s */\n" %(user_peripheral, register_name, reg['desc'], reg['resetVal']))
     C_file.write("#define  %s_%s            (*((volatile uint32_t*)(%s_BASE_ADDRESS + %s)))\n\n" %(user_peripheral, register_name, user_peripheral, reg['offset']))

     for bitfield_name in reg['field']:
        bitfield = reg['field'][bitfield_name]

        field_mask = 0xFFFFFFFF
        field_mask = field_mask << int(bitfield['width'])
        for i in range( 0, int(bitfield['offset']) ):
           field_mask = ((field_mask << 1 ) | 1)  & 0xFFFFFFFF  

        field_clear_mask = field_mask 
        
        field_mask = (~field_mask) & 0xFFFFFFFF
   
       
        #format the mask as 4 bytes uppercase hex 
        field_mask = "0x{0:0{1}X}".format(field_mask, 8)
        
        #format the mask as 4 bytes uppercase hex 
        field_clear_mask = "0x{0:0{1}X}".format(field_clear_mask, 8)   
        
        C_file.write("/* mask for bitfield \"%s.%s\"   (%s) */\n" %(register_name, bitfield_name, bitfield['desc']))
        C_file.write("#define  %s_%s_MASK         (%s)\n" %(register_name, bitfield_name, field_mask))
        C_file.write("#define  %s_%s_CLEAR_MASK   (%s)\n\n" %(register_name, bitfield_name, field_clear_mask))


else:
  print('ERROR: C file is already exist')

C_file.close()

