#*************************************************************************
#
# Builds the SEC_Call UNO Component.
#
# History:
#   Adapted from the SDK examples by Jim Kornelsen on 02/23/10
#     
#**************************************************************************

# Makefiles do not allow spaces in paths, so we use 8dot3 format.
#PRJ=C:/Program Files/OpenOffice.org 3 SDK/sdk
PRJ=C:/PROGRA~1/OPENOF~2.ORG/sdk
SETTINGS=$(PRJ)/settings

include $(SETTINGS)/settings.mk
include $(SETTINGS)/std.mk
include $(SETTINGS)/dk.mk

# Modify output directory that was set in std.mk
ifneq "$(OO_SDK_OUT)" ""
OUT=$(subst \,/,$(OO_SDK_OUT))/$(OS)lingtools.out
else
OUT=$(PRJ)/$(OS)lingtools.out
endif

OUT_BIN=$(OUT)/bin
OUT_INC=$(OUT)/inc
OUT_SLO=$(OUT)/slo
OUT_LIB=$(OUT)/lib
OUT_SLB=$(OUT)/slb
OUT_MISC=$(OUT)/misc
OUT_OBJ=$(OUT)/obj
OUT_CLASS=$(OUT)/class
COMP_PACKAGE_DIR=$(subst /,$(PS),$(OUT_BIN))

# Define non-platform/compiler specific settings
SAMPLE_NAME=SEC_Call_Component_Code
SAMPLE_INC_OUT=$(OUT_INC)/$(SAMPLE_NAME)
SAMPLE_GEN_OUT=$(OUT_MISC)/$(SAMPLE_NAME)
SAMPLE_SLO_OUT=$(OUT_SLO)/$(SAMPLE_NAME)
SAMPLE_OBJ_OUT=$(OUT_OBJ)/$(SAMPLE_NAME)

COMP_NAME=SEC_Call_Component
COMP_IMPL_NAME=$(COMP_NAME).uno.$(SHAREDLIB_EXT) 

APP1_NAME= Test_SEC_Call_Component
APP1_BINARY= $(OUT_BIN)/$(APP1_NAME)$(EXE_EXT)

COMP_RDB_NAME = $(COMP_NAME).uno.rdb
COMP_RDB = $(SAMPLE_GEN_OUT)/$(COMP_RDB_NAME)
COMP_PACKAGE = $(OUT_BIN)/$(COMP_NAME).$(UNOOXT_EXT)
COMP_PACKAGE_URL = $(subst \\,\,"$(COMP_PACKAGE_DIR)$(PS)$(COMP_NAME).$(UNOOXT_EXT)")
COMP_UNOPKG_MANIFEST = $(SAMPLE_GEN_OUT)/$(COMP_NAME)/META-INF/manifest.xml
COMP_MAPFILE = $(SAMPLE_GEN_OUT)/$(COMP_NAME).uno.map

COMP_REGISTERFLAG = $(SAMPLE_GEN_OUT)/devguide_$(COMP_NAME)_register_component.flag
COMP_TYPEFLAG = $(SAMPLE_GEN_OUT)/devguide_$(COMP_NAME)_types.flag

IDLFILES = lingtools.idl

CXXFILES = sec_call_impl.cxx

SLOFILES = $(patsubst %.cxx,$(SAMPLE_SLO_OUT)/%.$(OBJ_EXT),$(CXXFILES))

GENURDFILES = $(patsubst %.idl,$(SAMPLE_GEN_OUT)/%.urd,$(IDLFILES))

TYPELIST=-Tlingtools_module.XCallableSEC  \
	-Tlingtools_module.SEC_Call
 
# Targets
.PHONY: ALL
ALL : \
	$(SAMPLE_NAME)

include $(SETTINGS)/stdtarget.mk

$(SAMPLE_GEN_OUT)/%.urd : %.idl
	-$(MKDIR) $(subst /,$(PS),$(@D))
	$(IDLC) -I. -I$(IDL_DIR) -O$(SAMPLE_GEN_OUT) $<

$(SAMPLE_GEN_OUT)/%.rdb : $(GENURDFILES)
	-$(DEL) $(subst \\,\,$(subst /,$(PS),$@))
	-$(MKDIR) $(subst /,$(PS),$(@D))
	$(REGMERGE) $@ /UCR $(GENURDFILES)

$(COMP_TYPEFLAG) : $(COMP_RDB) $(SDKTYPEFLAG)
	-$(DEL) $(subst \\,\,$(subst /,$(PS),$@))
	-$(MKDIR) $(subst /,$(PS),$(@D))
	$(CPPUMAKER) -Gc -BUCR -O$(SAMPLE_INC_OUT) $(TYPESLIST) $(COMP_RDB) -X$(URE_TYPES) -X$(OFFICE_TYPES)
	echo flagged > $@

$(SAMPLE_SLO_OUT)/%.$(OBJ_EXT) : %.cxx $(COMP_TYPEFLAG)
	-$(MKDIR) $(subst /,$(PS),$(@D))
	$(CC) $(CC_FLAGS) $(CC_INCLUDES) -I$(SAMPLE_INC_OUT) $(CC_DEFINES) $(CC_OUTPUT_SWITCH)$(subst /,$(PS),$@) $<

$(COMP_MAPFILE) : $(SLOFILES)
	-$(MKDIR) $(subst /,$(PS),$(@D))
	cat $(PRJ)/settings/component.uno.map > $(COMP_MAPFILE) 
ifeq "$(OS)" "MACOSX"
	nm -gx $(SLOFILES) | $(ADDSYMBOLS) >> $(COMP_MAPFILE)
endif

ifeq "$(OS)" "WIN"
$(SHAREDLIB_OUT)/%.$(SHAREDLIB_EXT) : $(SLOFILES)
	-$(MKDIR) $(subst /,$(PS),$(@D))
	-$(MKDIR) $(subst /,$(PS),$(SAMPLE_GEN_OUT))
	$(LINK) $(COMP_LINK_FLAGS) /OUT:$@ \
	/MAP:$(SAMPLE_GEN_OUT)/$(subst $(SHAREDLIB_EXT),map,$(@F)) $(SLOFILES) \
	$(CPPUHELPERLIB) $(CPPULIB) $(SALLIB) $(STLPORTLIB) \
	msvcrt.lib kernel32.lib uuid.lib user32.lib
	$(LINK_MANIFEST)
else
$(SHAREDLIB_OUT)/%.$(SHAREDLIB_EXT) : $(SLOFILES) $(COMP_MAPFILE)
	-$(MKDIR) $(subst /,$(PS),$(@D)) && $(DEL) $(subst \\,\,$(subst /,$(PS),$@))
	$(LINK) $(COMP_LINK_FLAGS) $(LINK_LIBS) -o $@ $(SLOFILES) \
	$(CPPUHELPERLIB) $(CPPULIB) $(SALLIB) $(STLPORTLIB) $(STC++LIB) $(CPPUHELPERDYLIB) $(CPPUDYLIB) $(SALDYLIB)
ifeq "$(OS)" "MACOSX"
	$(INSTALL_NAME_URELIBS)  $@
endif
endif	

# rule for component package manifest
$(SAMPLE_GEN_OUT)/%/manifest.xml :
	-$(MKDIR) $(subst /,$(PS),$(@D))
	@echo $(OSEP)?xml version="$(QM)1.0$(QM)" encoding="$(QM)UTF-8$(QM)"?$(CSEP) > $@
	@echo $(OSEP)!DOCTYPE manifest:manifest PUBLIC "$(QM)-//OpenOffice.org//DTD Manifest 1.0//EN$(QM)" "$(QM)Manifest.dtd$(QM)"$(CSEP) >> $@
	@echo $(OSEP)manifest:manifest xmlns:manifest="$(QM)http://openoffice.org/2001/manifest$(QM)"$(CSEP) >> $@
	@echo $(SQM)  $(SQM)$(OSEP)manifest:file-entry manifest:media-type="$(QM)application/vnd.sun.star.uno-typelibrary;type=RDB$(QM)" >> $@
	@echo $(SQM)                       $(SQM)manifest:full-path="$(QM)$(subst /META-INF,,$(subst $(SAMPLE_GEN_OUT)/,,$(@D))).uno.rdb$(QM)"/$(CSEP) >> $@
	@echo $(SQM)  $(SQM)$(OSEP)manifest:file-entry manifest:media-type="$(QM)application/vnd.sun.star.uno-component;type=native;platform=$(UNOPKG_PLATFORM)$(QM)" >> $@
	@echo $(SQM)                       $(SQM)manifest:full-path="$(QM)$(subst /META-INF,,$(subst $(SAMPLE_GEN_OUT)/,,$(UNOPKG_PLATFORM)/$(@D))).uno.$(SHAREDLIB_EXT)$(QM)"/$(CSEP) >> $@
	@echo $(OSEP)/manifest:manifest$(CSEP) >> $@

$(COMP_PACKAGE) : $(SHAREDLIB_OUT)/$(COMP_IMPL_NAME) $(COMP_RDB) $(COMP_UNOPKG_MANIFEST)
	-$(DEL) $(subst \\,\,$(subst /,$(PS),$@))
	-$(MKDIR) $(subst /,$(PS),$(@D))
	-$(MKDIR) $(subst /,$(PS),$(SAMPLE_GEN_OUT)/$(UNOPKG_PLATFORM))	 
	$(COPY) $(subst /,$(PS),$<) $(subst /,$(PS),$(SAMPLE_GEN_OUT)/$(UNOPKG_PLATFORM))
	c: && cd $(subst /,$(PS),$(SAMPLE_GEN_OUT)) && $(SDK_ZIP) ../../bin/$(@F) $(COMP_RDB_NAME) $(UNOPKG_PLATFORM)/$(<F)
	c: && cd $(subst /,$(PS),$(SAMPLE_GEN_OUT)/$(subst .$(UNOOXT_EXT),,$(@F))) && $(SDK_ZIP) -u ../../../bin/$(@F) META-INF/manifest.xml


$(COMP_REGISTERFLAG) : $(COMP_PACKAGE)
ifeq "$(SDK_AUTO_DEPLOYMENT)" "YES"
	-$(DEL) $(subst \\,\,$(subst /,$(PS),$@))
	-$(MKDIR) $(subst /,$(PS),$(@D))
	$(DEPLOYTOOL) $(COMP_PACKAGE_URL)
	@echo flagged > $(subst /,$(PS),$@)
else
	@echo ----------------------------------------------------------------------
	@echo  If you want to install your component automatically, please set the
    @echo  environment variable SDK_AUTO_DEPLOYMENT = YES. But note that auto
    @echo  deployment is only 
	@echo  possible if no office instance is running. 
	@echo ----------------------------------------------------------------------
endif

$(SAMPLE_OBJ_OUT)/$(APP1_NAME).$(OBJ_EXT) : $(APP1_NAME).cxx $(COMP_TYPEFLAG)
	-$(MKDIR) $(subst /,$(PS),$(@D))
	$(CC) $(CC_FLAGS) $(CC_INCLUDES) -I$(SAMPLE_INC_OUT) $(CC_DEFINES) $(CC_OUTPUT_SWITCH)$(subst /,$(PS),$@) $<

$(OUT_BIN)/_$(APP1_NAME)$(EXE_EXT) : $(SAMPLE_OBJ_OUT)/$(APP1_NAME).$(OBJ_EXT)
	-$(MKDIR) $(subst /,$(PS),$(@D))
	-$(MKDIR) $(subst /,$(PS),$(SAMPLE_GEN_OUT))
ifeq "$(OS)" "WIN"
	$(LINK) $(EXE_LINK_FLAGS) /OUT:$@ \
	/MAP:$(SAMPLE_GEN_OUT)/$(basename $(@F)).map \
	$< $(CPPUHELPERLIB) $(CPPULIB) $(SALHELPERLIB) $(SALLIB) $(STLPORTLIB) \
	msvcrt.lib kernel32.lib uuid.lib user32.lib
else
	$(LINK) $(EXE_LINK_FLAGS) $(LINK_LIBS) -o $@ $< \
	  $(CPPUHELPERLIB) $(CPPULIB) $(SALHELPERLIB) $(SALLIB) $(STLPORTLIB) $(STDC++LIB) $(CPPUHELPERDYLIB) $(CPPUDYLIB) $(SALHELPERDYLIB) $(SALDYLIB)
ifeq "$(OS)" "MACOSX"
	$(INSTALL_NAME_URELIBS_BIN)  $@
endif
endif

$(OUT_BIN)/$(APP1_NAME)$(EXE_EXT) : $(OUT_BIN)/_$(APP1_NAME)$(EXE_EXT)
	$(COPY) $(subst /,$(PS),$(BIN_DIR)/unoapploader$(EXE_EXT)) $(subst /,$(PS),$@)
# touch the target to renew the date for correct dependencies.
# Note: no touch under windows! The unoapploader.exe is copied always.
ifneq "$(OS)" "WIN"
	touch $@
endif

$(SAMPLE_NAME) : $(COMP_REGISTERFLAG) $(APP1_BINARY)
	@echo ----------------------------------------------------------------------
	@echo Please use the following command to execute the example!
	@echo -
	@echo $(MAKE) $(APP1_NAME).run
	@echo --------
	@echo The simple C++ component was installed if SDK_AUTO_DEPLOYMENT = YES.
	@echo You can use this component inside your office installation, see the
	@echo example description.
	@echo ----------------------------------------------------------------------

%.run: $(OUT_BIN)/%$(EXE_EXT)
	$(subst /,$(PS),$(OUT_BIN))$(PS)$(basename $@)
	c: && cd $(subst /,$(PS),$(OUT_BIN)) && $(basename $@)

.PHONY: clean
clean :
	-$(DELRECURSIVE) $(subst /,$(PS),$(SAMPLE_INC_OUT))
	-$(DELRECURSIVE) $(subst /,$(PS),$(SAMPLE_GEN_OUT))
	-$(DELRECURSIVE) $(subst /,$(PS),$(SAMPLE_SLO_OUT))
	-$(DELRECURSIVE) $(subst /,$(PS),$(SAMPLE_OBJ_OUT))
	-$(DEL) $(subst \\,\,$(subst /,$(PS),$(OUT_BIN)/$(COMP_NAME)*))
	-$(DEL) $(subst \\,\,$(subst /,$(PS),$(OUT_BIN)/*$(APP1_NAME)*))
